#!/usr/bin/env python3
"""
Debug the database function directly to see what's happening
"""

import psycopg2.extras
from core.database import SentimentDatabase
from datetime import datetime

def debug_database_save():
    """Debug the database save function step by step"""
    print("=== Debugging Database Save Function ===")
    
    db = SentimentDatabase()
    
    test_article = {
        'title': 'Debug Test Article',
        'text': 'This is a debug test article to see what happens in the database function',
        'raw_extracted_text': 'Enhanced debug content',
        'extraction_successful': True,
        'source': 'Debug Source',
        'url': 'https://debug.com/test-function',
        'timestamp': datetime.now().isoformat(),
        'polarity': 0.3,
        'sentiment': 0.4,
        'sentiment_label': 'Positive',
        'text_length': 65,
        'extracted_length': 20,
        'enhancement_ratio': 1.3
    }
    
    symbol = 'DEBUGTEST'
    
    print(f"Testing with article: {test_article['title']}")
    print(f"URL: {test_article['url']}")
    print()
    
    # Debug the database function step by step
    with db.get_connection() as conn:
        with conn.cursor() as cursor:
            # Step 1: Create table
            print("Step 1: Creating symbol table...")
            cursor.execute("SELECT create_symbol_table(%s)", (symbol,))
            print("Table created successfully")
            
            # Step 2: Call the insert function directly
            print("\nStep 2: Calling insert function directly...")
            try:
                cursor.execute("""
                    SELECT insert_article_to_symbol_table(
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """, (
                    symbol,
                    test_article.get('title', ''),
                    test_article.get('text', ''),
                    test_article.get('raw_extracted_text', ''),
                    test_article.get('extraction_successful', False),
                    test_article.get('source', ''),
                    test_article.get('url', ''),
                    datetime.fromisoformat(test_article.get('timestamp')),
                    test_article.get('polarity', 0.0),
                    test_article.get('sentiment', 0.0),
                    test_article.get('sentiment_label', 'Neutral'),
                    test_article.get('text_length', 0),
                    test_article.get('extracted_length', 0),
                    test_article.get('enhancement_ratio', 0.0)
                ))
                
                result = cursor.fetchone()
                print(f"Raw result: {result}")
                print(f"Result type: {type(result)}")
                
                if result:
                    print(f"Result dir: {dir(result)}")
                    if hasattr(result, 'keys'):
                        print(f"Result keys: {list(result.keys())}")
                        print(f"Result values: {list(result.values())}")
                    if hasattr(result, '__getitem__'):
                        try:
                            print(f"result[0]: {result[0]}")
                        except Exception as e:
                            print(f"Error accessing result[0]: {e}")
                
            except Exception as e:
                print(f"Error in insert function: {e}")
                import traceback
                traceback.print_exc()
            
            conn.commit()
            
            # Step 3: Verify the article was saved
            print(f"\nStep 3: Checking if article was saved...")
            cursor.execute(f"SELECT COUNT(*) FROM articles_{symbol.lower()}")
            count_result = cursor.fetchone()
            print(f"Articles in table: {count_result}")
            
            cursor.execute(f"SELECT title, source, url FROM articles_{symbol.lower()} ORDER BY id DESC LIMIT 1")
            latest = cursor.fetchone()
            if latest:
                print(f"Latest article: {dict(latest)}")
            else:
                print("No articles found")

def main():
    debug_database_save()

if __name__ == "__main__":
    main()