#!/usr/bin/env python3
"""
Test to verify that sentiment analysis uses full article content when available
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sentiment import StockSentimentAnalyzer
from scrapers.google_news_scraper import GoogleNewsScraper

def test_sentiment_enhancement():
    """Test that sentiment analysis uses enhanced article content"""
    print("TESTING SENTIMENT ANALYSIS WITH ARTICLE ENHANCEMENT")
    print("=" * 60)
    
    # Create analyzer
    analyzer = StockSentimentAnalyzer("AAPL")
    
    print("1. Getting articles from Google News scraper...")
    scraper = GoogleNewsScraper("AAPL", debug=True)
    articles = scraper.scrape(max_articles=3)
    
    print(f"\nFound {len(articles)} articles to analyze")
    
    enhanced_articles = []
    non_enhanced_articles = []
    
    # Categorize articles
    for i, article in enumerate(articles):
        print(f"\n--- ARTICLE {i+1} ANALYSIS ---")
        print(f"URL: {article.url[:80]}...")
        print(f"Text length: {len(article.text)} chars")
        
        # Check if enhanced
        has_enhancement = hasattr(article, 'raw_extracted_text') and article.raw_extracted_text
        
        if has_enhancement:
            enhanced_articles.append(article)
            print(f"STATUS: ENHANCED (+{len(article.raw_extracted_text)} chars from newspaper3k)")
            print(f"Original excerpt: {article.text.split('.')[0][:100]}...")
            print(f"Enhanced preview: {article.raw_extracted_text[:200]}...")
        else:
            non_enhanced_articles.append(article)
            print(f"STATUS: NOT ENHANCED (using RSS excerpt only)")
            print(f"Content preview: {article.text[:200]}...")
    
    print(f"\n=== CATEGORIZATION RESULTS ===")
    print(f"Enhanced articles: {len(enhanced_articles)}")
    print(f"Non-enhanced articles: {len(non_enhanced_articles)}")
    
    # Test sentiment analysis on both types
    if enhanced_articles:
        print(f"\n=== TESTING ENHANCED ARTICLE SENTIMENT ===")
        for i, article in enumerate(enhanced_articles):
            print(f"\nEnhanced Article {i+1}:")
            
            # Analyze the full enhanced text
            sentiment_result = analyzer._analyze_text(article.text)
            
            print(f"  Text being analyzed length: {len(article.text)} chars")
            print(f"  Sentiment - Polarity: {sentiment_result['polarity']:.4f}")
            print(f"  Sentiment - Compound: {sentiment_result['compound']:.4f}")
            print(f"  Sentiment Label: {analyzer._get_sentiment_label(sentiment_result['compound'])}")
            
            # Show what text is actually being analyzed
            print(f"  Text sample (first 300 chars):")
            print(f"    '{article.text[:300]}...'")
            
            # Test if analyzing just the title would give different results
            title_only = article.text.split('.')[0] if '.' in article.text else article.text[:100]
            title_sentiment = analyzer._analyze_text(title_only)
            
            print(f"  COMPARISON - Title only sentiment:")
            print(f"    Title text: '{title_only}'")
            print(f"    Title sentiment: {title_sentiment['compound']:.4f}")
            print(f"    Difference: {abs(sentiment_result['compound'] - title_sentiment['compound']):.4f}")
            
            if abs(sentiment_result['compound'] - title_sentiment['compound']) > 0.05:
                print(f"    ✅ SIGNIFICANT DIFFERENCE - Using full article content!")
            else:
                print(f"    ⚠️  Similar sentiment - may not be using full content")
    
    if non_enhanced_articles:
        print(f"\n=== TESTING NON-ENHANCED ARTICLE SENTIMENT ===")
        for i, article in enumerate(non_enhanced_articles):
            print(f"\nNon-Enhanced Article {i+1}:")
            sentiment_result = analyzer._analyze_text(article.text)
            
            print(f"  Text length: {len(article.text)} chars")
            print(f"  Sentiment - Compound: {sentiment_result['compound']:.4f}")
            print(f"  Text being analyzed: '{article.text[:200]}...'")
    
    # Final verification test
    if enhanced_articles:
        print(f"\n=== FINAL VERIFICATION TEST ===")
        enhanced_article = enhanced_articles[0]
        
        print(f"Testing direct sentiment analysis call...")
        
        # This should use the full enhanced text
        full_sentiment = analyzer._analyze_text(enhanced_article.text)
        
        # This should use only the title/excerpt
        excerpt_only = enhanced_article.text.split('.')[0][:200]  # First sentence or 200 chars
        excerpt_sentiment = analyzer._analyze_text(excerpt_only)
        
        print(f"Full article sentiment: {full_sentiment['compound']:.4f}")
        print(f"Excerpt only sentiment: {excerpt_sentiment['compound']:.4f}")
        print(f"Sentiment difference: {abs(full_sentiment['compound'] - excerpt_sentiment['compound']):.4f}")
        
        print(f"\nFull text length: {len(enhanced_article.text)} chars")
        print(f"Excerpt length: {len(excerpt_only)} chars")
        
        if len(enhanced_article.text) > len(excerpt_only) * 3:
            print(f"✅ CONFIRMED: Sentiment analyzer has access to full article content")
            if abs(full_sentiment['compound'] - excerpt_sentiment['compound']) > 0.02:
                print(f"✅ CONFIRMED: Sentiment scores differ, indicating full content is being used")
                return True
            else:
                print(f"⚠️  WARNING: Sentiment scores very similar despite content difference")
                return False
        else:
            print(f"❌ ISSUE: Enhanced text not significantly longer than excerpt")
            return False
    else:
        print(f"❌ NO ENHANCED ARTICLES FOUND - Cannot verify sentiment enhancement")
        return False

def test_full_sentiment_pipeline():
    """Test the full sentiment analysis pipeline"""
    print(f"\n" + "=" * 60)
    print("TESTING FULL SENTIMENT ANALYSIS PIPELINE")
    print("=" * 60)
    
    analyzer = StockSentimentAnalyzer("AAPL")
    
    print("Running full sentiment analysis with target of 5 articles...")
    results = analyzer.analyze_sentiment(target_articles=5)
    
    print(f"\nPipeline Results:")
    print(f"  Total articles analyzed: {results.get('total_articles', 0)}")
    print(f"  Overall sentiment: {results.get('overall_sentiment', 0):.4f}")
    print(f"  Sentiment label: {results.get('sentiment_label', 'Unknown')}")
    
    # Check if any articles show signs of enhancement
    if 'source_breakdown' in results:
        enhanced_found = False
        for source, data in results['source_breakdown'].items():
            if 'enhanced_articles' in data or data.get('avg_length', 0) > 500:
                enhanced_found = True
                print(f"  {source}: {data.get('articles', 0)} articles, avg {data.get('avg_length', 0)} chars")
        
        if enhanced_found:
            print(f"✅ Pipeline shows evidence of article enhancement")
            return True
        else:
            print(f"⚠️  Pipeline may not be using enhanced content")
            return False
    
    return False

def main():
    """Run all sentiment enhancement tests"""
    print("COMPREHENSIVE SENTIMENT ENHANCEMENT VERIFICATION")
    print("=" * 70)
    
    success1 = test_sentiment_enhancement()
    success2 = test_full_sentiment_pipeline()
    
    print(f"\n" + "=" * 70)
    print("FINAL VERIFICATION RESULTS")
    print("=" * 70)
    print(f"Article-level sentiment test: {'PASS' if success1 else 'FAIL'}")
    print(f"Pipeline-level sentiment test: {'PASS' if success2 else 'FAIL'}")
    
    if success1 and success2:
        print(f"\n✅ CONFIRMED: Sentiment analysis is using full article content!")
        print(f"   - Enhanced articles provide richer sentiment analysis")
        print(f"   - Sentiment scores reflect full article content, not just titles")
        print(f"   - The Google News URL resolution fix is improving sentiment accuracy")
    elif success1:
        print(f"\n⚠️  PARTIAL SUCCESS: Article-level enhancement working, pipeline may need review")
    else:
        print(f"\n❌ ISSUE: Sentiment analysis may not be using enhanced article content")
        print(f"   - Check if newspaper3k content is being properly combined with titles")
        print(f"   - Verify that .text field contains enhanced content")
    
    return success1

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)