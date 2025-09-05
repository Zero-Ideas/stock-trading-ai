#!/usr/bin/env python3
"""
Debug Data Flow - Track exactly what data flows from scrapers to database
Shows the exact data being passed at each step to identify where articles are being lost
"""

from sentiment import StockSentimentAnalyzer
from datetime import datetime
import json

# Add debugging to the StockSentimentAnalyzer class
class DebugStockSentimentAnalyzer(StockSentimentAnalyzer):
    """Extended analyzer with debugging to track data flow"""
    
    def get_comprehensive_sentiment(self, target_articles: int = 50):
        """Override to add debugging at each step"""
        print(f"\n=== DEBUG: get_comprehensive_sentiment called ===")
        print(f"Target articles: {target_articles}")
        
        # Check database cache first (same as parent)
        all_sentiments = []
        if self.use_database and hasattr(self.db, 'get_recent_articles_from_db'):
            print(f"[DEBUG] Checking database cache...")
            try:
                recent_from_db = self.db.get_recent_articles_from_db(self.symbol, target_articles, 24)
                if recent_from_db and len(recent_from_db) >= target_articles // 2:
                    print(f"[DEBUG] Found {len(recent_from_db)} cached articles - using cache")
                    # Convert and return cached articles (same as parent)
                    for article in recent_from_db:
                        from scrapers.base_scraper import SentimentData
                        sentiment_obj = SentimentData(
                            text=article['text'],
                            polarity=article['polarity'],
                            compound=article['sentiment'],
                            source=article['source'],
                            url=article['url'],
                            timestamp=datetime.fromisoformat(article['timestamp'])
                        )
                        if article.get('raw_extracted_text'):
                            sentiment_obj.raw_extracted_text = article['raw_extracted_text']
                        all_sentiments.append(sentiment_obj)
                    return self._remove_duplicates(all_sentiments)
                else:
                    print(f"[DEBUG] Only {len(recent_from_db) if recent_from_db else 0} cached articles - fetching fresh")
            except Exception as e:
                print(f"[DEBUG] Cache check failed: {e}")
        
        # Prepare scraper tasks (same logic as parent)
        scraper_tasks = []
        articles_per_source = max(15, target_articles // len(self.scrapers) + 10)
        print(f"[DEBUG] Articles per source: {articles_per_source}")
        print(f"[DEBUG] Active scrapers: {len(self.scrapers)}")
        
        for name, scraper in self.scrapers.items():
            scraper_tasks.append((scraper, articles_per_source))
            print(f"[DEBUG]   - {name}: {scraper.source_name}")
        
        # Run scrapers sequentially for better debugging
        print(f"\n[DEBUG] Running scrapers sequentially for debugging...")
        
        for scraper, max_articles in scraper_tasks:
            print(f"\n[DEBUG] Testing {scraper.source_name}...")
            try:
                results = self._run_scraper_with_retry(scraper, max_articles)
                if results:
                    print(f"[DEBUG]   SUCCESS: {len(results)} articles from {scraper.source_name}")
                    all_sentiments.extend(results)
                    
                    # Show sample article
                    sample = results[0]
                    print(f"[DEBUG]   Sample: '{sample.text[:60]}...'")
                    print(f"[DEBUG]   URL: {sample.url}")
                    print(f"[DEBUG]   Source: '{sample.source}'")
                else:
                    print(f"[DEBUG]   FAILED: No articles from {scraper.source_name}")
                    
            except Exception as e:
                print(f"[DEBUG]   ERROR: {scraper.source_name} failed: {e}")
        
        print(f"\n[DEBUG] TOTAL ARTICLES COLLECTED: {len(all_sentiments)}")
        
        if not all_sentiments:
            print("[DEBUG] No articles collected - returning empty")
            return []
        
        # Remove duplicates
        print(f"[DEBUG] Removing duplicates...")
        unique_sentiments = self._remove_duplicates(all_sentiments)
        print(f"[DEBUG] After duplicate removal: {len(unique_sentiments)} articles")
        
        # Show what will be saved to database
        print(f"\n[DEBUG] PREPARING DATABASE SAVE...")
        if self.db and hasattr(self.db, 'save_articles_to_symbol_table'):
            articles_data = []
            for i, sentiment in enumerate(unique_sentiments):
                article_data = {
                    "title": sentiment.text.split('.')[0] if '.' in sentiment.text else sentiment.text[:100],
                    "text": sentiment.text,
                    "raw_extracted_text": getattr(sentiment, 'raw_extracted_text', ''),
                    "extraction_successful": hasattr(sentiment, 'raw_extracted_text') and sentiment.raw_extracted_text and len(sentiment.raw_extracted_text) > 100,
                    "source": sentiment.source,
                    "url": sentiment.url,
                    "timestamp": sentiment.timestamp.isoformat(),
                    "polarity": sentiment.polarity,
                    "sentiment": sentiment.compound,
                    "sentiment_label": self._get_sentiment_label(sentiment.compound),
                    "text_length": len(sentiment.text),
                    "extracted_length": len(getattr(sentiment, 'raw_extracted_text', '')),
                    "enhancement_ratio": round(len(getattr(sentiment, 'raw_extracted_text', '')) / max(1, len(sentiment.text)) * 100, 1) if hasattr(sentiment, 'raw_extracted_text') and sentiment.raw_extracted_text else 0.0
                }
                articles_data.append(article_data)
                
                # Show first few articles being saved
                if i < 3:
                    print(f"[DEBUG] Article {i+1} to save:")
                    print(f"[DEBUG]   Title: {article_data['title']}")
                    print(f"[DEBUG]   Source: {article_data['source']}")
                    print(f"[DEBUG]   URL: {article_data['url']}")
                    print(f"[DEBUG]   Text length: {article_data['text_length']}")
            
            print(f"[DEBUG] TOTAL ARTICLES TO SAVE: {len(articles_data)}")
            
            # Actually save to database
            try:
                new_articles_saved = self.db.save_articles_to_symbol_table(self.symbol, articles_data)
                print(f"[DEBUG] DATABASE SAVE RESULT: {new_articles_saved} new articles saved")
            except Exception as e:
                print(f"[DEBUG] DATABASE SAVE FAILED: {e}")
        
        print(f"\n[DEBUG] RETURNING {len(unique_sentiments)} articles to caller")
        return unique_sentiments

def test_data_flow():
    """Test the complete data flow with debugging"""
    print("=== Data Flow Debug Test ===")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Use a fresh symbol to avoid cache
    test_symbol = "META"  # Facebook/Meta - should be different from previous tests
    
    print(f"Testing data flow for {test_symbol}...")
    print("This will show exactly where articles are collected/saved/lost")
    print()
    
    # Check current database state
    from core.database import SentimentDatabase
    db = SentimentDatabase()
    existing_articles = db.get_recent_articles_from_db(test_symbol, 50, 24)
    print(f"Existing articles in {test_symbol} table: {len(existing_articles)}")
    
    # Create debug analyzer
    analyzer = DebugStockSentimentAnalyzer(test_symbol, use_database=True)
    
    # Run comprehensive sentiment with debugging
    print(f"\nRunning get_comprehensive_sentiment...")
    all_sentiments = analyzer.get_comprehensive_sentiment(target_articles=20)
    
    # Verify database after save
    print(f"\n=== POST-SAVE VERIFICATION ===")
    new_articles = db.get_recent_articles_from_db(test_symbol, 50, 1)  # Last hour
    print(f"Articles now in {test_symbol} table: {len(new_articles)}")
    
    if new_articles:
        print("Sample stored articles:")
        for i, article in enumerate(new_articles[:3]):
            print(f"  {i+1}. {article['title'][:50]}... ({article['source']})")
    
    # Summary
    print(f"\n=== SUMMARY ===")
    print(f"Collected by scrapers: {len(all_sentiments)}")
    print(f"Stored in database: {len(new_articles)}")
    
    if len(all_sentiments) == len(new_articles):
        print("✅ Perfect match - no articles lost in the process")
    elif len(new_articles) < len(all_sentiments):
        print(f"⚠️ {len(all_sentiments) - len(new_articles)} articles lost during database save")
    else:
        print(f"? Database has more articles than expected (possibly from previous runs)")
    
    return len(all_sentiments), len(new_articles)

if __name__ == "__main__":
    try:
        scraped, stored = test_data_flow()
        print(f"\nFinal result: {scraped} scraped → {stored} stored")
    except Exception as e:
        print(f"Debug test failed: {e}")
        import traceback
        traceback.print_exc()