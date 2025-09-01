#!/usr/bin/env python3
"""
Test sentiment analysis and examine output quality
"""

import sys
import os
import json

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sentiment import StockSentimentAnalyzer

def test_sentiment_analysis():
    """Test sentiment analysis with UNH and examine results"""
    print("TESTING SENTIMENT ANALYSIS WITH UNH")
    print("=" * 50)
    
    try:
        # Test with UNH (as seen in sentiment.py)
        analyzer = StockSentimentAnalyzer("UNH")
        print(f"Analyzing sentiment for {analyzer.symbol} ({analyzer.company_name})")
        
        # Run with moderate number of articles
        print("\nRunning analysis with 15 articles...")
        results = analyzer.analyze_sentiment(target_articles=15)
        
        print(f"\nBASIC RESULTS:")
        print(f"  Total articles: {results.get('total_articles', 0)}")
        print(f"  Overall sentiment: {results.get('overall_sentiment', 'N/A')}")
        print(f"  Average compound: {results.get('sentiment_scores', {}).get('average_compound', 0):.4f}")
        print(f"  Sentiment distribution: {results.get('sentiment_distribution', {})}")
        
        # Get the latest JSON file to examine detailed results
        data_dir = "./Data"
        json_files = [f for f in os.listdir(data_dir) if f.startswith(f"sentiment_analysis_{analyzer.symbol}") and f.endswith('.json')]
        
        if json_files:
            latest_json = sorted(json_files)[-1]
            json_path = os.path.join(data_dir, latest_json)
            
            print(f"\nExamining detailed results from: {latest_json}")
            
            with open(json_path, 'r', encoding='utf-8') as f:
                detailed_data = json.load(f)
            
            # Analyze the raw articles for sentiment accuracy
            raw_articles = detailed_data.get('raw_articles', [])
            
            print(f"\nDETAILED ANALYSIS OF {len(raw_articles)} ARTICLES:")
            
            neutral_issues = []
            positive_issues = []
            negative_issues = []
            
            for i, article in enumerate(raw_articles[:10]):  # Examine first 10
                title = article.get('title', 'No title')
                sentiment_label = article.get('sentiment_label', 'Unknown')
                compound = article.get('compound', 0)
                text_length = article.get('text_length', 0)
                extraction_successful = article.get('extraction_successful', False)
                source = article.get('source', 'Unknown')
                
                print(f"\nArticle {i+1}:")
                print(f"  Title: {title}")
                print(f"  Source: {source}")
                print(f"  Sentiment: {sentiment_label} ({compound:.4f})")
                print(f"  Text length: {text_length} chars")
                print(f"  Enhanced: {'Yes' if extraction_successful else 'No'}")
                
                # Analyze for potential sentiment issues
                title_lower = title.lower()
                
                # Check for potentially misclassified neutral articles
                if sentiment_label == "Neutral":
                    positive_indicators = ['growth', 'profit', 'beat', 'exceed', 'strong', 'gain', 'rise', 'up', 'surge', 'rally']
                    negative_indicators = ['loss', 'decline', 'fall', 'drop', 'miss', 'weak', 'down', 'concern', 'risk', 'crash']
                    
                    has_positive = any(word in title_lower for word in positive_indicators)
                    has_negative = any(word in title_lower for word in negative_indicators)
                    
                    if has_positive or has_negative:
                        neutral_issues.append({
                            'title': title,
                            'compound': compound,
                            'has_positive': has_positive,
                            'has_negative': has_negative,
                            'text_length': text_length
                        })
                        print(f"    POTENTIAL ISSUE: Marked neutral but has sentiment indicators")
                
                # Check for potentially misclassified positive/negative
                elif sentiment_label in ["Positive", "Very Positive"] and compound < 0.05:
                    positive_issues.append({'title': title, 'compound': compound, 'label': sentiment_label})
                    print(f"    POTENTIAL ISSUE: Marked positive but low compound score")
                
                elif sentiment_label in ["Negative", "Very Negative"] and compound > -0.05:
                    negative_issues.append({'title': title, 'compound': compound, 'label': sentiment_label})
                    print(f"    POTENTIAL ISSUE: Marked negative but compound score near neutral")
            
            # Summary of potential issues
            print(f"\nSENTIMENT ANALYSIS ISSUES DETECTED:")
            print(f"  Potentially misclassified neutral: {len(neutral_issues)}")
            print(f"  Potentially misclassified positive: {len(positive_issues)}")
            print(f"  Potentially misclassified negative: {len(negative_issues)}")
            
            if neutral_issues:
                print(f"\n  Neutral classification issues:")
                for issue in neutral_issues[:3]:  # Show first 3
                    print(f"    '{issue['title']}' - compound: {issue['compound']:.4f}")
                    print(f"    Has positive words: {issue['has_positive']}, Has negative words: {issue['has_negative']}")
            
            return len(neutral_issues) + len(positive_issues) + len(negative_issues) == 0
        
        else:
            print("No JSON files found to analyze")
            return False
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run sentiment analysis test"""
    success = test_sentiment_analysis()
    
    print(f"\n{'='*50}")
    if success:
        print("SUCCESS: Sentiment analysis appears accurate")
    else:
        print("ISSUES DETECTED: Sentiment analysis may need calibration")
    print(f"{'='*50}")
    
    return success

if __name__ == "__main__":
    main()