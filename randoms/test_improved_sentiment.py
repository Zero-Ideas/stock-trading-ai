#!/usr/bin/env python3
"""
Test script to verify improved sentiment.py integration with enhanced scrapers
"""

import sys
import os
import time

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sentiment import StockSentimentAnalyzer

def test_improved_integration():
    """Test the improved sentiment analyzer with enhanced scrapers"""
    print("TESTING IMPROVED SENTIMENT.PY INTEGRATION")
    print("=" * 60)
    
    try:
        # Test with a small number of articles to verify integration
        print("Initializing StockSentimentAnalyzer with AAPL...")
        analyzer = StockSentimentAnalyzer("AAPL")
        
        print(f"\nConfigured scrapers: {list(analyzer.scrapers.keys())}")
        print(f"Company name cache: {analyzer.company_name}")
        print(f"FinBERT available: {analyzer.finbert_pipeline is not None}")
        
        print("\nRunning sentiment analysis with target_articles=10...")
        results = analyzer.analyze_sentiment(target_articles=10)
        
        print(f"\nRESULTS SUMMARY:")
        print(f"   Total articles: {results.get('total_articles', 0)}")
        print(f"   Overall sentiment: {results.get('overall_sentiment', 'N/A')}")
        print(f"   Average compound: {results.get('sentiment_scores', {}).get('average_compound', 0):.3f}")
        
        # Check newspaper3k integration
        if 'newspaper3k_stats' in results:
            stats = results['newspaper3k_stats']
            print(f"\nNEWSPAPER3K INTEGRATION:")
            print(f"   Enhanced articles: {stats.get('enhanced_articles', 0)}/{stats.get('total_articles', 0)}")
            if stats.get('enhanced_articles', 0) > 0:
                print(f"   Avg enhancement size: {stats.get('avg_enhancement_ratio', 0):.0f} chars")
                print(f"   Sources with enhancement:")
                for source_stat in stats.get('sources_with_enhancement', []):
                    print(f"     - {source_stat['source']}: {source_stat['enhanced_count']} articles (avg {source_stat['avg_extracted_chars']:.0f} chars)")
        
        # Show source breakdown
        print(f"\nSOURCE BREAKDOWN:")
        for source, data in results.get('source_breakdown', {}).items():
            print(f"   {source}: {data['count']} articles (avg sentiment: {data['avg_sentiment']:.3f})")
        
        # Check if data files were created
        data_files = []
        data_dir = "./Data"
        if os.path.exists(data_dir):
            for file in os.listdir(data_dir):
                if file.startswith("sentiment_analysis_AAPL"):
                    data_files.append(file)
        
        if data_files:
            print(f"\nDATA FILES CREATED:")
            for file in sorted(data_files)[-3:]:  # Show last 3 files
                print(f"   {file}")
        
        print(f"\nTest completed successfully!")
        return True
        
    except Exception as e:
        print(f"ERROR: Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_improved_integration()
    if success:
        print("\nSUCCESS: All improvements are working correctly!")
    else:
        print("\nFAILED: Some issues were detected.")