#!/usr/bin/env python3
"""
Test database save directly with the exact data structure sentiment.py uses
"""

from core.database import SentimentDatabase
from scrapers.base_scraper import SentimentData
from datetime import datetime, timedelta
import random

def test_direct_database_save():
    """Test the exact database save process that sentiment.py uses"""
    print("=== Direct Database Save Test (QCOM) ===")
    print("Testing the exact save process that sentiment.py should be doing")
    print()
    
    # Create mock sentiment data (same as scrapers would return)
    mock_sentiments = []
    sources = ["Google News", "NewsAPI", "Yahoo Finance", "Bloomberg", "MarketWatch"]
    
    for i in range(8):
        timestamp = datetime.now() - timedelta(hours=random.randint(1, 12))
        sentiment_score = random.uniform(-0.6, 0.8)
        
        mock_article = SentimentData(
            text=f"QCOM article {i+1}: Strong quarterly earnings and market performance indicate positive outlook for Qualcomm's business growth in the semiconductor sector.",
            source=sources[i % len(sources)],
            timestamp=timestamp,
            polarity=sentiment_score * 0.8,
            compound=sentiment_score,
            url=f"https://test-direct.com/qcom/article-{i+1}"
        )
        
        # Add newspaper3k enhancement to some articles
        if i % 3 == 0:
            mock_article.raw_extracted_text = f"Enhanced content from newspaper3k for QCOM article {i+1}. Additional market analysis and detailed financial information extracted from the full article."
        
        mock_sentiments.append(mock_article)
    
    print(f"Created {len(mock_sentiments)} mock sentiment articles")
    
    # Now replicate the EXACT database save process from sentiment.py
    print(f"\n[DEBUG] DATABASE SAVE PROCESS - BEFORE PREPARING DATA")
    print(f"[DEBUG] unique_sentiments count: {len(mock_sentiments)}")
    print(f"[DEBUG] Symbol: QCOM")
    
    db = SentimentDatabase()
    
    if db and hasattr(db, 'save_articles_to_symbol_table'):
        try:
            articles_data = []
            print(f"\n[DEBUG] Preparing articles for database save...")
            
            for i, sentiment in enumerate(mock_sentiments):
                # This is the EXACT same logic as sentiment.py lines 624-639
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
                    "sentiment_label": _get_sentiment_label(sentiment.compound),
                    "text_length": len(sentiment.text),
                    "extracted_length": len(getattr(sentiment, 'raw_extracted_text', '')),
                    "enhancement_ratio": round(len(getattr(sentiment, 'raw_extracted_text', '')) / max(1, len(sentiment.text)) * 100, 1) if hasattr(sentiment, 'raw_extracted_text') and sentiment.raw_extracted_text else 0.0
                }
                articles_data.append(article_data)
                
                # Debug first 3 articles being prepared
                if i < 3:
                    print(f"[DEBUG] Article {i+1} prepared for save:")
                    print(f"[DEBUG]   Title: {article_data['title']}")
                    print(f"[DEBUG]   Source: {article_data['source']}")
                    print(f"[DEBUG]   URL: {article_data['url']}")
                    print(f"[DEBUG]   Text length: {article_data['text_length']}")
                    print(f"[DEBUG]   Sentiment: {article_data['sentiment']}")
            
            print(f"\n[DEBUG] TOTAL ARTICLES PREPARED FOR SAVE: {len(articles_data)}")
            print(f"[DEBUG] Articles data structure ready, calling save_articles_to_symbol_table...")
            
            # Save to per-symbol table (EXACT same call as sentiment.py)
            new_articles_saved = db.save_articles_to_symbol_table("QCOM", articles_data)
            print(f"[DATABASE] SAVE COMPLETE: {new_articles_saved} new articles saved to QCOM table")
            
            # Verify what was actually saved (EXACT same verification as sentiment.py)
            print(f"\n[DEBUG] VERIFYING DATABASE SAVE...")
            try:
                saved_articles = db.get_recent_articles_from_db("QCOM", 50, 1)  # Last 1 hour
                print(f"[DEBUG] VERIFICATION: {len(saved_articles)} articles found in QCOM table")
                
                if len(saved_articles) != new_articles_saved:
                    print(f"[WARNING] MISMATCH: Expected {new_articles_saved} saved, but found {len(saved_articles)} in table")
                else:
                    print(f"[SUCCESS] MATCH: Save count matches table count")
                    
                # Show what was actually saved
                if saved_articles:
                    print(f"[DEBUG] Sample saved articles:")
                    for i, article in enumerate(saved_articles[:3]):
                        print(f"[DEBUG]   Saved {i+1}: {article['title'][:50]}... ({article['source']})")
                        
                return len(saved_articles)
                        
            except Exception as ve:
                print(f"[ERROR] Verification failed: {ve}")
                return 0
            
        except Exception as e:
            print(f"[WARNING] Failed to save articles to per-symbol table: {e}")
            import traceback
            traceback.print_exc()
            return 0
    else:
        print(f"[WARNING] Database save skipped - db={db}, has_method={hasattr(db, 'save_articles_to_symbol_table') if db else False}")
        return 0

def _get_sentiment_label(compound: float) -> str:
    """Same sentiment label function as sentiment.py"""
    if compound > 0.75:
        return "Very Positive"
    elif compound > 0.05:
        return "Positive"
    elif -0.05 < compound < 0.05:
        return "Neutral"
    elif compound < -0.05:
        return "Negative"
    else:
        return "Very Negative"

if __name__ == "__main__":
    saved_count = test_direct_database_save()
    
    print(f"\n=== FINAL RESULT ===")
    if saved_count > 0:
        print(f"SUCCESS: {saved_count} articles saved to QCOM table")
        print("The database save process is working correctly")
        print("Issue must be that sentiment.py is not calling this save logic")
    else:
        print("FAILURE: No articles were saved")
        print("There is an issue with the database save process itself")
    
    print(f"\nCheck 'articles_qcom' table in pgAdmin4 to verify")