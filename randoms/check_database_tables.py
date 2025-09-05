#!/usr/bin/env python3
"""
Database Table Checker
Checks what tables exist and their structure in the PostgreSQL database
"""

import psycopg2
import psycopg2.extras
from core.database import SentimentDatabase

def main():
    """Check database tables and structure"""
    print("=== Database Table Structure Check ===")
    print()
    
    try:
        # Initialize database
        db = SentimentDatabase()
        
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                # Check all tables in the database
                print("1. All tables in database:")
                cursor.execute("""
                    SELECT table_name, table_type
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    ORDER BY table_name;
                """)
                
                tables = cursor.fetchall()
                for table in tables:
                    print(f"   {table['table_name']} ({table['table_type']})")
                
                print()
                
                # Check for per-symbol article tables
                print("2. Per-symbol article tables:")
                cursor.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name LIKE 'articles_%'
                    ORDER BY table_name;
                """)
                
                symbol_tables = cursor.fetchall()
                if symbol_tables:
                    for table in symbol_tables:
                        table_name = table['table_name']
                        symbol = table_name.replace('articles_', '').upper()
                        
                        # Count articles in this table
                        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                        result = cursor.fetchone()
                        if hasattr(result, '__getitem__'):
                            count = result[0]
                        elif hasattr(result, 'count'):
                            count = result.count
                        else:
                            count = 0
                        
                        # Get most recent article timestamp
                        cursor.execute(f"""
                            SELECT MAX(article_timestamp) 
                            FROM {table_name}
                        """)
                        result = cursor.fetchone()
                        latest = result[0] if result else None
                        latest_str = latest.strftime('%Y-%m-%d %H:%M:%S') if latest else 'N/A'
                        
                        print(f"   {table_name} ({symbol}): {count} articles, latest: {latest_str}")
                        
                        # Show column structure for first table
                        if table_name == symbol_tables[0]['table_name']:
                            print(f"     Columns in {table_name}:")
                            cursor.execute(f"""
                                SELECT column_name, data_type, is_nullable
                                FROM information_schema.columns
                                WHERE table_name = '{table_name}'
                                ORDER BY ordinal_position;
                            """)
                            columns = cursor.fetchall()
                            for col in columns:
                                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                                print(f"       {col['column_name']}: {col['data_type']} {nullable}")
                else:
                    print("   No per-symbol article tables found")
                
                print()
                
                # Check main tables content
                print("3. Main tables content:")
                
                # Check sentiment_analyses table
                cursor.execute("SELECT COUNT(*) FROM sentiment_analyses")
                result = cursor.fetchone()
                analyses_count = result[0] if result else 0
                print(f"   sentiment_analyses: {analyses_count} records")
                
                if analyses_count > 0:
                    cursor.execute("""
                        SELECT symbol, analysis_timestamp, total_articles, overall_sentiment
                        FROM sentiment_analyses
                        ORDER BY analysis_timestamp DESC
                        LIMIT 5
                    """)
                    recent_analyses = cursor.fetchall()
                    print("     Recent analyses:")
                    for analysis in recent_analyses:
                        timestamp = analysis['analysis_timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                        print(f"       {analysis['symbol']}: {analysis['total_articles']} articles, "
                              f"{analysis['overall_sentiment']}, {timestamp}")
                
                # Check sentiment_articles table
                cursor.execute("SELECT COUNT(*) FROM sentiment_articles")
                result = cursor.fetchone()
                articles_count = result[0] if result else 0
                print(f"   sentiment_articles: {articles_count} records")
                
                print()
                
                # Check database functions
                print("4. Database functions:")
                cursor.execute("""
                    SELECT routine_name, routine_type
                    FROM information_schema.routines
                    WHERE routine_schema = 'public'
                    AND routine_name LIKE '%symbol%'
                    ORDER BY routine_name;
                """)
                
                functions = cursor.fetchall()
                for func in functions:
                    print(f"   {func['routine_name']} ({func['routine_type']})")
                
                print()
                
                # Test a function
                print("5. Testing database functions:")
                try:
                    cursor.execute("SELECT generate_url_hash('https://example.com/test')")
                    result = cursor.fetchone()
                    hash_result = result[0] if result else None
                    print(f"   generate_url_hash: [OK] (sample: {hash_result[:16]}...)")
                except Exception as e:
                    print(f"   generate_url_hash: [ERROR] {e}")
                
                try:
                    cursor.execute("SELECT create_symbol_table('TEST')")
                    print(f"   create_symbol_table: [OK]")
                    
                    # Check if TEST table was created
                    cursor.execute("""
                        SELECT EXISTS(
                            SELECT 1 FROM information_schema.tables 
                            WHERE table_name = 'articles_test'
                        )
                    """)
                    result = cursor.fetchone()
                    exists = result[0] if result else False
                    print(f"   articles_test table created: {'[OK]' if exists else '[ERROR]'}")
                    
                except Exception as e:
                    print(f"   create_symbol_table: [ERROR] {e}")
                
        print()
        print("[SUCCESS] Database structure check completed")
        
    except Exception as e:
        print(f"[ERROR] Error checking database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()