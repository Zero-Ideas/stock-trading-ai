#!/usr/bin/env python3
"""
PostgreSQL Database Interface for Stock Sentiment Analysis
Handles caching and persistence of sentiment analysis results
"""

import psycopg2
import psycopg2.extras
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import json
import os
import sys
from contextlib import contextmanager
import hashlib

class SentimentDatabase:
    """PostgreSQL database interface for sentiment analysis caching"""
    
    def __init__(self, 
                 host: str = None,
                 port: int = None,
                 database: str = None,
                 username: str = None,
                 password: str = None):
        """Initialize database connection parameters"""
        # Try to load configuration from multiple sources
        config = self._load_config()
        
        self.host = host or config.get('host', 'localhost')
        self.port = port or config.get('port', 5432)
        self.database = database or config.get('database', 'stock_sentiment')
        self.username = username or config.get('username', 'postgres')
        self.password = password or config.get('password') or os.getenv('POSTGRES_PASSWORD')
        
        # Try common passwords if none provided
        if not self.password:
            common_passwords = ['postgres', '', 'admin', 'password']
            for pwd in common_passwords:
                if self._try_connection(pwd):
                    self.password = pwd
                    break
            
            if not self.password:
                self._show_config_help()
                raise Exception("Could not connect to PostgreSQL. Please check the configuration instructions above.")
        
        # Test connection on init
        self._test_connection()
        
    def _load_config(self) -> Dict:
        """Load database configuration from various sources"""
        config = {}
        
        # Try to import database_config.py
        try:
            # Add current directory to path
            current_dir = os.path.dirname(os.path.dirname(__file__))
            if current_dir not in sys.path:
                sys.path.insert(0, current_dir)
            
            import database_config
            if hasattr(database_config, 'POSTGRES_CONFIG'):
                config = database_config.POSTGRES_CONFIG
                print(f"[CONFIG] Loaded database configuration from database_config.py")
            
        except ImportError:
            # No database_config.py file found
            pass
        except Exception as e:
            print(f"[WARNING] Error loading database_config.py: {e}")
        
        return config
    
    def _show_config_help(self):
        """Show configuration help to user"""
        print("\n" + "="*60)
        print("PostgreSQL CONNECTION FAILED")
        print("="*60)
        print("Could not connect to PostgreSQL with common passwords.")
        print("\nTo fix this, please choose one of these options:")
        print()
        print("OPTION 1: Set environment variable")
        print("  set POSTGRES_PASSWORD=your_postgres_password")
        print()
        print("OPTION 2: Create database_config.py file")
        print("  1. Copy database_config_example.py to database_config.py")
        print("  2. Edit database_config.py and set your password")
        print()
        print("OPTION 3: Test your PostgreSQL connection manually")
        print("  psql -U postgres -d postgres -h localhost")
        print("\nYour PostgreSQL service is running, but authentication failed.")
        print("="*60 + "\n")
    
    def _try_connection(self, password: str) -> bool:
        """Try connection with given password"""
        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database='postgres',  # Connect to default database first
                user=self.username,
                password=password
            )
            conn.close()
            return True
        except:
            return False
    
    def _test_connection(self) -> bool:
        """Test database connection and create database if it doesn't exist"""
        try:
            # First try to connect to the specific database
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.username,
                password=self.password
            )
            conn.close()
            print(f"[SUCCESS] Connected to PostgreSQL database '{self.database}'")
            return True
            
        except psycopg2.OperationalError as e:
            if "does not exist" in str(e):
                # Database doesn't exist, try to create it
                try:
                    self._create_database()
                    print(f"[SUCCESS] Created and connected to PostgreSQL database '{self.database}'")
                    return True
                except Exception as create_error:
                    print(f"[ERROR] Failed to create database: {create_error}")
                    return False
            else:
                print(f"[ERROR] Database connection failed: {e}")
                print(f"[HINT] Make sure PostgreSQL is running and the password is correct.")
                print(f"[HINT] You can set POSTGRES_PASSWORD environment variable.")
                return False
        except Exception as e:
            print(f"[ERROR] Database connection error: {e}")
            return False
    
    def _create_database(self):
        """Create the database if it doesn't exist"""
        # Connect to default postgres database to create our database
        conn = psycopg2.connect(
            host=self.host,
            port=self.port,
            database='postgres',  # Connect to default database
            user=self.username,
            password=self.password
        )
        conn.autocommit = True
        
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE {self.database}")
        
        conn.close()
        
        # Now initialize the schema
        self.initialize_schema()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.username,
                password=self.password,
                cursor_factory=psycopg2.extras.RealDictCursor
            )
            yield conn
        finally:
            if conn:
                conn.close()
    
    def initialize_schema(self):
        """Initialize database schema from SQL file"""
        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Schemas", "database_schema.sql")
        
        if not os.path.exists(schema_path):
            raise FileNotFoundError(f"Database schema file not found: {schema_path}")
        
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(schema_sql)
            conn.commit()
        
        print("[SUCCESS] Database schema initialized successfully")
    
    def save_articles_to_partitioned_table(self, symbol: str, articles_data: List[Dict]) -> int:
        """
        Save articles to partitioned table with duplicate URL checking
        
        Args:
            symbol: Stock symbol
            articles_data: List of article data dictionaries
            
        Returns:
            Number of new articles saved (excluding duplicates)
        """
        if not articles_data:
            return 0
            
        new_articles_count = 0
        duplicates_count = 0
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                for article in articles_data:
                    try:
                        # Use the database function to insert with duplicate checking
                        cursor.execute("""
                            SELECT insert_article_partitioned(
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                            )
                        """, (
                            symbol,
                            article.get('title', article.get('text', '')[:100]),
                            article.get('text', ''),
                            article.get('raw_extracted_text', ''),
                            bool(article.get('extraction_successful', False)),  # Ensure proper boolean
                            article.get('source', ''),
                            article.get('url', ''),
                            datetime.fromisoformat(article.get('timestamp', datetime.utcnow().isoformat())),
                            float(article.get('polarity', 0.0)),  # Ensure proper float
                            float(article.get('sentiment', 0.0)),  # Map 'sentiment' to compound, ensure float
                            article.get('sentiment_label', 'Neutral'),
                            int(article.get('text_length', len(article.get('text', '')))),  # Ensure proper int
                            int(article.get('extracted_length', 0)),  # Ensure proper int
                            float(article.get('enhancement_ratio', 0.0))  # Ensure proper float
                        ))
                        
                        result = cursor.fetchone()
                        if result:
                            # Handle RealDictRow result from PostgreSQL function
                            if hasattr(result, 'keys') and 'insert_article_partitioned' in result:
                                result_id = result['insert_article_partitioned']
                            elif hasattr(result, 'values') and result.values():
                                result_id = list(result.values())[0]
                            else:
                                result_id = 0
                        else:
                            result_id = 0
                        if result_id > 0:
                            new_articles_count += 1
                        else:
                            duplicates_count += 1
                            
                    except Exception as e:
                        print(f"[WARNING] Failed to save article to partitioned table for {symbol}: {e}")
                        continue
            
            conn.commit()
        
        print(f"[DATABASE] Saved {new_articles_count} new articles to partitioned table for {symbol} (skipped {duplicates_count} duplicates)")
        return new_articles_count
    
    def save_articles_to_symbol_table(self, symbol: str, articles_data: List[Dict]) -> int:
        """
        DEPRECATED: Use save_articles_to_partitioned_table instead
        Kept for backward compatibility - redirects to partitioned version
        """
        print(f"[DEPRECATED] save_articles_to_symbol_table called - redirecting to partitioned table")
        return self.save_articles_to_partitioned_table(symbol, articles_data)
    
    def get_recent_articles_from_db(self, symbol: str, max_articles: int, max_hours: int = 24) -> List[Dict]:
        """
        Get recent articles from partitioned table
        
        Args:
            symbol: Stock symbol
            max_articles: Maximum number of articles to retrieve
            max_hours: Maximum age of articles in hours
            
        Returns:
            List of article dictionaries
        """
        articles = []
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT * FROM get_recent_articles_partitioned(%s, %s, %s)
                    """, (symbol, max_articles, max_hours))
                    
                    rows = cursor.fetchall()
                    for row in rows:
                        articles.append({
                            "title": row['title'],
                            "text": row['full_text'],
                            "raw_extracted_text": row['raw_extracted_text'],
                            "extraction_successful": row['extraction_successful'],
                            "source": row['source'],
                            "url": row['url'],
                            "timestamp": row['article_timestamp'].isoformat(),
                            "polarity": float(row['polarity']),
                            "sentiment": float(row['compound']),
                            "sentiment_label": row['sentiment_label'],
                            "text_length": row['text_length'],
                            "extracted_length": row['extracted_length'],
                            "enhancement_ratio": float(row['enhancement_ratio'])
                        })
                        
        except Exception as e:
            print(f"[WARNING] Failed to get recent articles from partitioned table for {symbol}: {e}")
            # Legacy fallback no longer available after table migration
        
        return articles
    
    def check_url_exists(self, symbol: str, url: str) -> bool:
        """
        Check if URL already exists in partitioned table
        
        Args:
            symbol: Stock symbol
            url: URL to check
            
        Returns:
            True if URL exists, False otherwise
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT url_exists_partitioned(%s, %s)
                    """, (symbol, url))
                    
                    result = cursor.fetchone()
                    if hasattr(result, 'keys') and 'url_exists_partitioned' in result:
                        return bool(result['url_exists_partitioned'])
                    elif hasattr(result, 'values') and result.values():
                        return bool(list(result.values())[0])
                    else:
                        return bool(result[0]) if result else False
                    
        except Exception as e:
            print(f"[WARNING] Failed to check URL existence in partitioned table for {symbol}: {e}")
            return False
    
    def get_cached_analysis(self, symbol: str, max_age_hours: float = 1.0) -> Optional[Dict]:
        """
        Get cached sentiment analysis if it exists and is recent enough
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            max_age_hours: Maximum age in hours for cached data (default 1.0)
            
        Returns:
            Cached analysis dict or None if not found or too old
        """
        # Try to get cached analysis with articles from partitioned table
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT * FROM get_cached_analysis_with_articles_partitioned(%s, %s)
                    """, (symbol.upper(), max_age_hours))
                    
                    row = cursor.fetchone()
                    print(row)
                    if row:
                        # Parse articles data from JSONB
                        articles_data = row['articles_data'] if row['articles_data'] else []
                        
                        # Format recent articles (top 5)
                        recent_articles = []
                        for i, article in enumerate(articles_data[:5]):
                            recent_articles.append({
                                "text": article['title'] if len(article['title']) <= 200 else article['title'][:200] + "...",
                                "sentiment": float(article['compound']),
                                "source": article['source'],
                                "url": article['url'],
                                "timestamp": article['article_timestamp'],
                                "ID": article['analysis_id']
                            })
                        
                        # Format raw articles
                        raw_articles = []
                        for article in articles_data:
                            raw_articles.append({
                                "text": article['full_text'],
                                "sentiment": float(article['compound']),
                                "source": article['source'],
                                "url": article['url'],
                                "timestamp": article['article_timestamp'],
                                "ID": article['analysis_id']
                            })
                        
                        # Build result dictionary
                        result = {
                            "symbol": row['symbol'],
                            "company_name": row['company_name'],
                            "analysis_timestamp": row['analysis_timestamp'].isoformat(),
                            "total_articles": len(articles_data) if articles_data else row['total_articles'],
                            "overall_sentiment": row['overall_sentiment'],
                            "sentiment_scores": {
                                "average_sentiment": float(row['average_sentiment']),
                                "weighted_avg_from_sources": float(row['weighted_avg_from_sources'])
                            },
                            "sentiment_distribution": {
                                "positive": row['positive_count'],
                                "negative": row['negative_count'],
                                "neutral": row['neutral_count'],
                                "positive_percentage": float(row['positive_percentage']),
                                "negative_percentage": float(row['negative_percentage']),
                                "neutral_percentage": float(row['neutral_percentage'])
                            },
                            "source_breakdown": row['source_breakdown'],
                            "recent_articles": recent_articles,
                            "raw_articles": raw_articles,
                            "cached": True,
                            "cache_age_minutes": (datetime.utcnow() - row['analysis_timestamp'].replace(tzinfo=None)).total_seconds() / 60
                        }
                        
                        return result
        except Exception as e:
            print(f"[WARNING] Failed to get cached analysis with partitioned table: {e}")
            # Legacy fallback no longer available after table migration
            
        # No fallback available after table migration
        return None
    
    def save_analysis(self, analysis_data: Dict, articles_data: List[Dict]) -> int:
        """
        Save sentiment analysis results to database
        
        Args:
            analysis_data: Main analysis results dictionary
            articles_data: List of individual article data
            
        Returns:
            analysis_id of the saved record
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Insert main analysis record
                insert_analysis_sql = """
                    INSERT INTO sentiment_analyses (
                        symbol, company_name, target_articles, total_articles, overall_sentiment,
                        average_sentiment, weighted_avg_from_sources,
                        positive_count, negative_count, neutral_count,
                        positive_percentage, negative_percentage, neutral_percentage,
                        source_breakdown, newspaper3k_stats
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    ) RETURNING id
                """
                
                cursor.execute(insert_analysis_sql, (
                    analysis_data['symbol'],
                    analysis_data['company_name'],
                    analysis_data.get('target_articles', 50),
                    analysis_data['total_articles'],
                    analysis_data['overall_sentiment'],
                    analysis_data['sentiment_scores']['average_sentiment'],
                    analysis_data['sentiment_scores']['weighted_avg_from_sources'],
                    analysis_data['sentiment_distribution']['positive'],
                    analysis_data['sentiment_distribution']['negative'],
                    analysis_data['sentiment_distribution']['neutral'],
                    analysis_data['sentiment_distribution']['positive_percentage'],
                    analysis_data['sentiment_distribution']['negative_percentage'],
                    analysis_data['sentiment_distribution']['neutral_percentage'],
                    json.dumps(analysis_data['source_breakdown']),
                    json.dumps(analysis_data.get('newspaper3k_stats', {}))
                ))
                
                analysis_id = cursor.fetchone()['id']
                
                # Articles are now stored in the partitioned table separately
                # The save_articles_to_partitioned_table method handles article storage
                # This method only saves the analysis summary to sentiment_analyses table
                
            conn.commit()
            
        print(f"[SUCCESS] Saved analysis for {analysis_data['symbol']} (ID: {analysis_id}) with {len(articles_data)} articles")
        return analysis_id
    
    def get_analysis_history(self, symbol: str, limit: int = 10) -> List[Dict]:
        """Get analysis history for a symbol"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        id,
                        symbol,
                        company_name,
                        analysis_timestamp,
                        total_articles,
                        overall_sentiment,
                        average_sentiment,
                        positive_percentage,
                        negative_percentage,
                        neutral_percentage
                    FROM sentiment_analyses
                    WHERE symbol = %s
                    ORDER BY analysis_timestamp DESC
                    LIMIT %s
                """, (symbol.upper(), limit))
                
                return [dict(row) for row in cursor.fetchall()]
    
    def cleanup_old_analyses(self, days_old: int = 30):
        """Remove analyses older than specified days"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM sentiment_analyses 
                    WHERE analysis_timestamp < %s
                """, (datetime.utcnow() - timedelta(days=days_old),))
                
                deleted_count = cursor.rowcount
            conn.commit()
        
        print(f"[SUCCESS] Cleaned up {deleted_count} analyses older than {days_old} days")
        return deleted_count
    
    
    
    def get_migration_status(self) -> Dict:
        """
        Get status of migration from per-symbol tables to partitioned table
        """
        status = {
            "partitioned_table_exists": False,
            "legacy_tables": [],
            "partitioned_article_count": 0,
            "legacy_article_count": 0,
            "symbols_migrated": []
        }
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Check if partitioned table exists
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT 1 FROM information_schema.tables 
                            WHERE table_schema = 'public'
                            AND table_name = 'articles_partitioned'
                        )
                    """)
                    result = cursor.fetchone()
                    if hasattr(result, 'keys') and 'exists' in result:
                        status["partitioned_table_exists"] = result['exists']
                    else:
                        status["partitioned_table_exists"] = result[0] if result else False
                    
                    if status["partitioned_table_exists"]:
                        # Get article count in partitioned table
                        cursor.execute("SELECT COUNT(*) FROM articles_partitioned")
                        count_result = cursor.fetchone()
                        status["partitioned_article_count"] = count_result['count'] if hasattr(count_result, 'keys') else count_result[0]
                        
                        # Get symbols in partitioned table
                        cursor.execute("SELECT DISTINCT symbol FROM articles_partitioned ORDER BY symbol")
                        symbol_rows = cursor.fetchall()
                        status["symbols_migrated"] = [row['symbol'] if hasattr(row, 'keys') else row[0] for row in symbol_rows]
                    
                    # Get legacy tables
                    cursor.execute("""
                        SELECT table_name, 
                               replace(table_name, 'articles_', '') as symbol
                        FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name LIKE 'articles_%'
                        AND table_name != 'articles_partitioned'
                        ORDER BY table_name
                    """)
                    
                    legacy_tables = cursor.fetchall()
                    for table_row in legacy_tables:
                        table_name = table_row['table_name'] if hasattr(table_row, 'keys') else table_row[0]
                        symbol = table_row[1] if hasattr(table_row, '__len__') else table_name.replace('articles_', '')
                        
                        # Get count for each legacy table
                        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                        count_result = cursor.fetchone()
                        count = count_result['count'] if hasattr(count_result, 'keys') else count_result[0]
                        status["legacy_tables"].append({
                            "table_name": table_name,
                            "symbol": symbol,
                            "article_count": count
                        })
                        status["legacy_article_count"] += count
                        
        except Exception as e:
            print(f"[WARNING] Failed to get migration status: {e}")
        
        return status