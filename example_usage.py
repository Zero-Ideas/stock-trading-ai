#!/usr/bin/env python3
"""
Example usage of the IndustryAnalyzer class
Demonstrates how to integrate industry analysis into other Python applications
"""

import os
from industry_analysis import IndustryAnalyzer

# Make sure to set your API keys
os.environ["OPENAI_API_KEY"] = "your-openai-key-here"
os.environ["GEMINI_API_KEY"] = "your-gemini-key-here"

def analyze_company_industry(symbol: str):
    """
    Analyze a company's industry sentiment
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL', 'MSFT')
    
    Returns:
        dict: Analysis results
    """
    try:
        with IndustryAnalyzer(company_symbol=symbol) as analyzer:
            results = analyzer.analyze_industry()
            return {
                'success': True,
                'data': results
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def analyze_specific_industry(industry: str, company_context: str = None):
    """
    Analyze sentiment for a specific industry
    
    Args:
        industry: Industry name (e.g., 'Technology', 'Healthcare')
        company_context: Optional company symbol for context
    
    Returns:
        dict: Analysis results
    """
    try:
        with IndustryAnalyzer() as analyzer:
            if company_context:
                # Analyze with company context
                results = analyzer.analyze_industry(
                    industry=industry, 
                    target_company_symbol=company_context
                )
            else:
                # Analyze industry directly
                results = analyzer.analyze_industry(industry=industry)
            
            return {
                'success': True,
                'data': results
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def get_industry_dashboard():
    """
    Get a dashboard overview of all industries
    
    Returns:
        dict: Industry overview data
    """
    try:
        with IndustryAnalyzer() as analyzer:
            overview = analyzer.get_industry_overview()
            return {
                'success': True,
                'data': overview,
                'summary': {
                    'total_industries': len(overview),
                    'positive_industries': sum(1 for data in overview.values() 
                                             if 'positive' in data['latest_sentiment'].lower()),
                    'negative_industries': sum(1 for data in overview.values() 
                                             if 'negative' in data['latest_sentiment'].lower()),
                    'neutral_industries': sum(1 for data in overview.values() 
                                            if 'neutral' in data['latest_sentiment'].lower())
                }
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def batch_analyze_companies(symbols: list):
    """
    Analyze multiple companies at once
    
    Args:
        symbols: List of stock symbols
    
    Returns:
        dict: Batch analysis results
    """
    results = {}
    
    for symbol in symbols:
        print(f"Analyzing {symbol}...")
        result = analyze_company_industry(symbol)
        
        if result['success']:
            results[symbol] = {
                'company_name': result['data']['company_name'],
                'industry': result['data']['industry'],
                'sentiment': result['data']['sentiment_label'],
                'score': result['data']['overall_sentiment'],
                'confidence': result['data']['confidence_score']
            }
        else:
            results[symbol] = {
                'error': result['error']
            }
    
    return results

def main():
    """Demonstration of various usage patterns"""
    
    print("=== IndustryAnalyzer Usage Examples ===\n")
    
    # Example 1: Single company analysis
    print("1. Single Company Analysis:")
    result = analyze_company_industry("AAPL")
    if result['success']:
        data = result['data']
        print(f"   {data['company_name']}: {data['sentiment_label']} ({data['overall_sentiment']:.2f})")
    else:
        print(f"   Error: {result['error']}")
    
    print()
    
    # Example 2: Direct industry analysis
    print("2. Direct Industry Analysis:")
    result = analyze_specific_industry("Healthcare")
    if result['success']:
        data = result['data']
        print(f"   Healthcare Industry: {data['sentiment_label']} ({data['overall_sentiment']:.2f})")
        print(f"   Key trends: {len(data['key_trends'])} identified")
    else:
        print(f"   Error: {result['error']}")
    
    print()
    
    # Example 3: Industry dashboard
    print("3. Industry Dashboard:")
    dashboard = get_industry_dashboard()
    if dashboard['success']:
        summary = dashboard['summary']
        print(f"   Total industries tracked: {summary['total_industries']}")
        print(f"   Positive: {summary['positive_industries']}, Negative: {summary['negative_industries']}, Neutral: {summary['neutral_industries']}")
        
        # Show top 3 industries by sentiment
        industries = dashboard['data']
        sorted_industries = sorted(industries.items(), key=lambda x: x[1]['latest_score'], reverse=True)
        print("   Top 3 industries by sentiment:")
        for industry, data in sorted_industries[:3]:
            print(f"     {industry}: {data['latest_sentiment']} ({data['latest_score']:.2f})")
    else:
        print(f"   Error: {dashboard['error']}")
    
    print()
    
    # Example 4: Batch analysis
    print("4. Batch Company Analysis:")
    companies = ["GOOGL", "MSFT", "TSLA"]
    batch_results = batch_analyze_companies(companies)
    
    for symbol, data in batch_results.items():
        if 'error' not in data:
            print(f"   {symbol} ({data['company_name']}): {data['industry']} - {data['sentiment']}")
        else:
            print(f"   {symbol}: Error - {data['error']}")

if __name__ == "__main__":
    # Note: This example won't run without valid API keys
    # Uncomment and set your API keys at the top of the file to test
    print("Please set your API keys in the script to run this example.")
    # main()