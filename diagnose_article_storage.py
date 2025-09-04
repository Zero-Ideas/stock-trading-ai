#!/usr/bin/env python3
"""
Diagnose Article Storage Issues
Checks what articles are being saved and identifies any data loss issues
"""

from datetime import datetime, timedelta
from core.database import SentimentDatabase
import json

def main():
    """Diagnose article storage"""
    print("=== Article Storage Diagnosis ===")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Initialize database
        db = SentimentDatabase()
        
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                # Check all per-symbol tables and their row counts
                print("1. Per-symbol table analysis:")
                cursor.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name LIKE 'articles_%'
                    ORDER BY table_name;
                """)
                
                symbol_tables = cursor.fetchall()
                total_articles = 0
                
                for table in symbol_tables:
                    table_name = table['table_name']
                    symbol = table_name.replace('articles_', '').upper()
                    
                    # Count total articles
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                    count_result = cursor.fetchone()
                    count = count_result['count']
                    total_articles += count
                    
                    print(f"   {symbol} ({table_name}): {count} articles")
                    
                    if count > 0:
                        # Show sample article with all data
                        cursor.execute(f"""
                            SELECT title, source, url, polarity, compound, 
                                   sentiment_label, text_length, extracted_length,
                                   article_timestamp, enhancement_ratio
                            FROM {table_name}
                            ORDER BY article_timestamp DESC
                            LIMIT 1
                        """)
                        sample = cursor.fetchone()
                        if sample:
                            print(f"     Latest article:")
                            print(f"       Title: {sample['title'][:60]}...")
                            print(f"       Source: '{sample['source']}'")
                            print(f"       URL: {sample['url']}")
                            print(f"       Sentiment: {sample['compound']:.3f} ({sample['sentiment_label']})")
                            print(f"       Text length: {sample['text_length']} chars")
                            if sample['extracted_length'] > 0:
                                print(f"       newspaper3k enhanced: +{sample['extracted_length']} chars")
                            print(f"       Timestamp: {sample['article_timestamp']}")
                        
                        # Check source distribution
                        cursor.execute(f"""
                            SELECT source, COUNT(*) as count
                            FROM {table_name}
                            GROUP BY source
                            ORDER BY count DESC
                        """)
                        sources = cursor.fetchall()
                        source_list = [f"{s['source']}({s['count']})" for s in sources]
                        print(f"     Sources: {', '.join(source_list)}")
                    
                    print()
                
                print(f"Total articles across all per-symbol tables: {total_articles}")
                print()
                
                # Check main analysis table
                print("2. Main analysis table:")
                cursor.execute("SELECT COUNT(*) as count FROM sentiment_analyses")
                analyses_count = cursor.fetchone()['count']
                print(f"   sentiment_analyses table: {analyses_count} records")
                
                if analyses_count > 0:
                    cursor.execute("""
                        SELECT symbol, total_articles, overall_sentiment,
                               analysis_timestamp, source_breakdown
                        FROM sentiment_analyses
                        ORDER BY analysis_timestamp DESC
                        LIMIT 3
                    """)
                    recent_analyses = cursor.fetchall()
                    print("   Recent analyses:")
                    for analysis in recent_analyses:
                        print(f"     {analysis['symbol']}: {analysis['total_articles']} articles, "
                              f"{analysis['overall_sentiment']}, {analysis['analysis_timestamp']}")
                        # Parse source breakdown
                        if analysis['source_breakdown']:
                            if isinstance(analysis['source_breakdown'], str):
                                sources = json.loads(analysis['source_breakdown'])
                            else:
                                sources = analysis['source_breakdown']
                            source_info = [f"{name}({data['count']})" for name, data in sources.items()]
                            print(f"       Sources: {', '.join(source_info)}")
                
                print()
                
                # Check legacy articles table
                print("3. Legacy articles table:")
                cursor.execute("SELECT COUNT(*) as count FROM sentiment_articles")
                legacy_count = cursor.fetchone()['count']
                print(f"   sentiment_articles table: {legacy_count} records")
                
                if legacy_count > 0:
                    cursor.execute("""
                        SELECT symbol, source, COUNT(*) as count
                        FROM sentiment_articles
                        GROUP BY symbol, source
                        ORDER BY symbol, count DESC
                    """)
                    legacy_breakdown = cursor.fetchall()
                    print("   Breakdown:")
                    for item in legacy_breakdown:
                        print(f"     {item['symbol']} - {item['source']}: {item['count']} articles")
                
                print()
                
                # Check if we're missing articles (comparison)
                print("4. Data integrity check:")
                if analyses_count > 0:
                    cursor.execute("""
                        SELECT symbol, total_articles 
                        FROM sentiment_analyses
                        ORDER BY analysis_timestamp DESC
                        LIMIT 1
                    """)
                    latest_analysis = cursor.fetchone()
                    if latest_analysis:
                        expected_articles = latest_analysis['total_articles']
                        symbol = latest_analysis['symbol']
                        
                        # Check actual articles in per-symbol table
                        cursor.execute(f"SELECT COUNT(*) as count FROM articles_{symbol.lower()}")
                        actual_articles = cursor.fetchone()['count']
                        
                        print(f"   Latest analysis for {symbol}:")
                        print(f"     Expected articles (from analysis): {expected_articles}")
                        print(f"     Actual articles (in per-symbol table): {actual_articles}")
                        
                        if actual_articles < expected_articles:
                            print(f"     ⚠ POTENTIAL DATA LOSS: {expected_articles - actual_articles} articles missing")
                        elif actual_articles == expected_articles:
                            print(f"     ✓ Article counts match - no data loss detected")
                        else:
                            print(f"     ? More articles in table than expected analysis")
        
        print()
        print("5. Diagnosis Summary:")
        if total_articles == 0:
            print("   [WARNING] No articles found in any per-symbol table")
            print("   This suggests no sentiment analysis has been run recently")
        elif total_articles < 10:
            print(f"   [WARNING] Only {total_articles} articles found")
            print("   This may indicate article loss or limited scraping")
        else:
            print(f"   [OK] Found {total_articles} articles across all symbols")
            print("   Database appears to be storing articles properly")
        
    except Exception as e:
        print(f"[ERROR] Diagnosis failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()