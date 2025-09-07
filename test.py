#!/usr/bin/env python3
"""
Test script using the new IndustryAnalyzer class
Demonstrates how to use the class-based approach for industry analysis
"""

import os
from industry_analysis import IndustryAnalyzer

# Set API keys
os.environ["OPENAI_API_KEY"] = "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"
os.environ["GEMINI_API_KEY"] = "AIzaSyA91d_s6glh9j8de5CDoxB12lFbTziLn50"

def main():
    """Main function demonstrating the IndustryAnalyzer class"""
    
    # Example 1: Analyze industry for a specific company
    print("=== EXAMPLE 1: Company-specific Analysis ===")
    company_symbol = "JPM"
    
    try:
        # Initialize analyzer with a company symbol
        with IndustryAnalyzer(company_symbol=company_symbol) as analyzer:
            # Analyze the company's industry
            results = analyzer.analyze_industry()
            
            print(f"\nAnalysis Results:")
            print(f"Company: {results['company_name']} ({results['company_symbol']})")
            print(f"Industry: {results['industry']}")
            print(f"Sentiment: {results['sentiment_label']} ({results['overall_sentiment']:.3f})")
            print(f"Confidence: {results['confidence_score']:.2f}")
            print(f"Key Trends: {len(results['key_trends'])} trends identified")
            
    except Exception as e:
        print(f"Error in company analysis: {e}")
    
    print("\n" + "="*60 + "\n")
    
    # Example 2: Direct industry analysis (demonstrating caching)
    print("=== EXAMPLE 2: Direct Industry Analysis (with Caching) ===")
    
    try:
        # Initialize analyzer without specific company
        with IndustryAnalyzer() as analyzer:
            # First analysis - should use API
            print("\n--- First Analysis (Fresh) ---")
            results1 = analyzer.analyze_industry(industry="Technology")
            
            print(f"Analysis Results:")
            print(f"Industry: {results1['industry']}")
            print(f"Sentiment: {results1['sentiment_label']} ({results1['overall_sentiment']:.3f})")
            print(f"Confidence: {results1['confidence_score']:.2f}")
            print(f"Data source: {'Cached' if results1.get('cached') else 'Fresh API call'}")
            
            # Second analysis immediately - should use cache
            print("\n--- Second Analysis (Should be cached) ---")
            results2 = analyzer.analyze_industry(industry="Technology")
            
            print(f"Analysis Results:")
            print(f"Industry: {results2['industry']}")
            print(f"Sentiment: {results2['sentiment_label']} ({results2['overall_sentiment']:.3f})")
            print(f"Data source: {'Cached' if results2.get('cached') else 'Fresh API call'}")
            if results2.get('cached'):
                print(f"Cache age: {results2.get('cache_age_hours', 0):.2f} hours")
            
            # Third analysis with force refresh - should use API

    except Exception as e:
        print(f"Error in industry analysis: {e}")
    
    print("\n" + "="*60 + "\n")
    
    # Example 3: Get recent analyses and overview
    print("=== EXAMPLE 3: Recent Analyses and Overview ===")
    
    try:
        with IndustryAnalyzer() as analyzer:
            # Get industry overview
            overview = analyzer.get_industry_overview()
            print(f"Industry Overview - {len(overview)} industries with data:")
            
            for industry, data in list(overview.items())[:5]:  # Show first 5
                print(f"  {industry}: {data['latest_sentiment']} ({data['latest_score']:.2f})")
            
            # Get recent analyses for a specific industry
            if overview:
                sample_industry = list(overview.keys())[0]
                recent = analyzer.get_recent_industry_analysis(sample_industry, limit=3)
                print(f"\nRecent analyses for {sample_industry}: {len(recent)} found")
                
                for analysis in recent[:2]:  # Show first 2
                    print(f"  {analysis['created_at']}: {analysis['sentiment_label']} ({analysis['overall_sentiment']:.2f})")
            
    except Exception as e:
        print(f"Error getting overview: {e}")

if __name__ == "__main__":
    main()
