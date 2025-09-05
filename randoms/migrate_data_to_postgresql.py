#!/usr/bin/env python3
"""
Data Migration Script: JSON Files to PostgreSQL
Migrates existing sentiment analysis data from ./Data directory to PostgreSQL database
"""

import os
import json
import glob
from datetime import datetime
from typing import List, Dict, Optional
import argparse

# Import database functionality
try:
    from core.database import SentimentDatabase
    DATABASE_AVAILABLE = True
except ImportError as e:
    print(f"ERROR: Database module not available: {e}")
    print("Please ensure PostgreSQL is installed and configured correctly.")
    exit(1)


class SentimentDataMigrator:
    """Migrates sentiment analysis data from JSON files to PostgreSQL"""
    
    def __init__(self):
        """Initialize database connection"""
        self.db = SentimentDatabase()
        
    def find_json_files(self, data_dir: str = "./Data") -> List[str]:
        """Find all sentiment analysis JSON files"""
        if not os.path.exists(data_dir):
            print(f"Data directory not found: {data_dir}")
            return []
        
        # Look for sentiment analysis JSON files (not summary or articles CSV)
        pattern = os.path.join(data_dir, "sentiment_analysis_*.json")
        files = glob.glob(pattern)
        
        print(f"Found {len(files)} JSON files to migrate from {data_dir}")
        return sorted(files)
    
    def parse_json_file(self, file_path: str) -> Optional[Dict]:
        """Parse a single JSON file and extract analysis data"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate required fields
            required_fields = ['symbol', 'total_articles', 'overall_sentiment', 'sentiment_scores']
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                print(f"WARNING: {file_path} missing required fields: {missing_fields}")
                return None
            
            # Extract file metadata
            filename = os.path.basename(file_path)
            # Example: sentiment_analysis_AAPL_20250901_131735.json
            parts = filename.replace('.json', '').split('_')
            if len(parts) >= 4:
                symbol = parts[2]
                date_str = parts[3]
                time_str = parts[4] if len(parts) > 4 else "000000"
                
                # Parse timestamp
                try:
                    file_timestamp = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
                except ValueError:
                    print(f"WARNING: Could not parse timestamp from {filename}")
                    file_timestamp = datetime.utcnow()
            else:
                print(f"WARNING: Unexpected filename format: {filename}")
                file_timestamp = datetime.utcnow()
                symbol = data.get('symbol', 'UNKNOWN')
            
            # Use file timestamp if analysis_timestamp is not present or invalid
            if 'analysis_timestamp' not in data:
                data['analysis_timestamp'] = file_timestamp.isoformat()
            
            return {
                'file_path': file_path,
                'file_timestamp': file_timestamp,
                'data': data
            }
            
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON in {file_path}: {e}")
            return None
        except Exception as e:
            print(f"ERROR: Failed to process {file_path}: {e}")
            return None
    
    def migrate_single_analysis(self, parsed_data: Dict) -> bool:
        """Migrate a single analysis to the database"""
        try:
            data = parsed_data['data']
            file_path = parsed_data['file_path']
            
            # Check if this analysis already exists
            symbol = data['symbol']
            analysis_timestamp = datetime.fromisoformat(data['analysis_timestamp'].replace('Z', '+00:00'))
            
            # Handle missing fields in older formats
            sentiment_scores = data.get('sentiment_scores', {})
            
            # For older files without sentiment_scores structure
            if not isinstance(sentiment_scores, dict) or not sentiment_scores:
                # Try to extract from top-level if available
                avg_sentiment = data.get('average_sentiment', 0.0)
                sentiment_scores = {
                    'average_sentiment': avg_sentiment,
                    'weighted_avg_from_sources': avg_sentiment  # Use same value as fallback
                }
            
            # Ensure required sentiment_scores fields exist
            sentiment_scores.setdefault('average_sentiment', 0.0)
            sentiment_scores.setdefault('weighted_avg_from_sources', 0.0)
            
            # Prepare analysis data
            analysis_data = {
                'symbol': symbol,
                'company_name': data.get('company_name', symbol),
                'target_articles': data.get('target_articles', 50),
                'total_articles': data['total_articles'],
                'overall_sentiment': data['overall_sentiment'],
                'sentiment_scores': sentiment_scores,
                'sentiment_distribution': data.get('sentiment_distribution', {
                    'positive': 0,
                    'negative': 0,
                    'neutral': 0,
                    'positive_percentage': 0.0,
                    'negative_percentage': 0.0,
                    'neutral_percentage': 0.0
                }),
                'source_breakdown': data.get('source_breakdown', {}),
                'newspaper3k_stats': data.get('newspaper3k_stats', {})
            }
            
            # Prepare articles data
            articles_data = []
            raw_articles = data.get('raw_articles', [])
            
            for article in raw_articles:
                articles_data.append({
                    'title': article.get('text', '')[:100],  # First 100 chars as title
                    'text': article.get('text', ''),
                    'raw_extracted_text': article.get('raw_extracted_text', ''),
                    'extraction_successful': bool(article.get('raw_extracted_text')) and len(article.get('raw_extracted_text', '')) > 100,
                    'source': article.get('source', ''),
                    'url': article.get('url', ''),
                    'timestamp': article.get('timestamp', analysis_timestamp.isoformat()),
                    'polarity': article.get('polarity', 0.0),
                    'sentiment': article.get('sentiment', 0.0),  # compound score
                    'sentiment_label': self._get_sentiment_label(article.get('sentiment', 0.0)),
                    'text_length': len(article.get('text', '')),
                    'extracted_length': len(article.get('raw_extracted_text', '')),
                    'enhancement_ratio': round(len(article.get('raw_extracted_text', '')) / max(1, len(article.get('text', ''))) * 100, 1) if article.get('raw_extracted_text') else 0.0
                })
            
            # Save to database
            analysis_id = self.db.save_analysis(analysis_data, articles_data)
            
            print(f"[SUCCESS] Migrated: {os.path.basename(file_path)} -> DB ID {analysis_id} ({len(articles_data)} articles)")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to migrate {parsed_data['file_path']}: {e}")
            return False
    
    def _get_sentiment_label(self, compound: float) -> str:
        """Convert compound score to readable sentiment label"""
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
    
    def migrate_all(self, data_dir: str = "./Data", dry_run: bool = False) -> Dict[str, int]:
        """Migrate all JSON files to PostgreSQL"""
        stats = {
            'total_files': 0,
            'successful_migrations': 0,
            'failed_migrations': 0,
            'skipped_files': 0
        }
        
        json_files = self.find_json_files(data_dir)
        stats['total_files'] = len(json_files)
        
        if not json_files:
            print("No JSON files found to migrate.")
            return stats
        
        print(f"\nStarting migration of {len(json_files)} files...")
        if dry_run:
            print("DRY RUN MODE - No data will be written to database")
        
        for file_path in json_files:
            try:
                parsed_data = self.parse_json_file(file_path)
                
                if not parsed_data:
                    stats['skipped_files'] += 1
                    continue
                
                if dry_run:
                    print(f"DRY RUN: Would migrate {os.path.basename(file_path)} ({parsed_data['data']['symbol']}, {parsed_data['data']['total_articles']} articles)")
                    stats['successful_migrations'] += 1
                else:
                    if self.migrate_single_analysis(parsed_data):
                        stats['successful_migrations'] += 1
                    else:
                        stats['failed_migrations'] += 1
                        
            except Exception as e:
                print(f"[ERROR] Unexpected error processing {file_path}: {e}")
                stats['failed_migrations'] += 1
        
        return stats
    
    def verify_migration(self, symbol: Optional[str] = None) -> None:
        """Verify migrated data by showing database contents"""
        print("\n=== MIGRATION VERIFICATION ===")
        
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                if symbol:
                    cursor.execute("""
                        SELECT symbol, analysis_timestamp, total_articles, overall_sentiment,
                               positive_percentage, negative_percentage, neutral_percentage
                        FROM sentiment_analyses 
                        WHERE symbol = %s
                        ORDER BY analysis_timestamp DESC
                        LIMIT 10
                    """, (symbol.upper(),))
                    print(f"Recent analyses for {symbol.upper()}:")
                else:
                    cursor.execute("""
                        SELECT symbol, analysis_timestamp, total_articles, overall_sentiment,
                               positive_percentage, negative_percentage, neutral_percentage
                        FROM sentiment_analyses 
                        ORDER BY analysis_timestamp DESC
                        LIMIT 20
                    """)
                    print("Recent analyses (all symbols):")
                
                rows = cursor.fetchall()
                
                if rows:
                    print(f"{'Symbol':<8} {'Timestamp':<20} {'Articles':<8} {'Sentiment':<15} {'Pos%':<6} {'Neg%':<6} {'Neu%':<6}")
                    print("-" * 80)
                    
                    for row in rows:
                        timestamp = row['analysis_timestamp'].strftime('%Y-%m-%d %H:%M')
                        print(f"{row['symbol']:<8} {timestamp:<20} {row['total_articles']:<8} {row['overall_sentiment']:<15} {row['positive_percentage']:<6.1f} {row['negative_percentage']:<6.1f} {row['neutral_percentage']:<6.1f}")
                else:
                    print("No data found in database.")
                
                # Show summary stats
                cursor.execute("SELECT COUNT(*) as total_analyses, COUNT(DISTINCT symbol) as unique_symbols FROM sentiment_analyses")
                summary = cursor.fetchone()
                cursor.execute("SELECT COUNT(*) as total_articles FROM sentiment_articles")
                articles_count = cursor.fetchone()
                
                print(f"\nDatabase Summary:")
                print(f"  - Total analyses: {summary['total_analyses']}")
                print(f"  - Unique symbols: {summary['unique_symbols']}")
                print(f"  - Total articles: {articles_count['total_articles']}")


def main():
    """Main function with CLI interface"""
    parser = argparse.ArgumentParser(
        description='Migrate sentiment analysis data from JSON files to PostgreSQL',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python migrate_data_to_postgresql.py                    # Migrate all files
  python migrate_data_to_postgresql.py --dry-run          # Preview migration
  python migrate_data_to_postgresql.py --verify           # Verify existing data
  python migrate_data_to_postgresql.py --verify AAPL      # Verify specific symbol
  python migrate_data_to_postgresql.py --data-dir ./Data  # Custom data directory
        """
    )
    
    parser.add_argument('--data-dir', default='./Data', help='Directory containing JSON files (default: ./Data)')
    parser.add_argument('--dry-run', action='store_true', help='Preview migration without writing to database')
    parser.add_argument('--verify', nargs='?', const='', help='Verify migrated data (optionally for specific symbol)')
    
    args = parser.parse_args()
    
    try:
        migrator = SentimentDataMigrator()
        
        if args.verify is not None:
            # Verification mode
            symbol = args.verify if args.verify else None
            migrator.verify_migration(symbol)
            return
        
        # Migration mode
        print("=== SENTIMENT DATA MIGRATION TO POSTGRESQL ===")
        
        # Perform migration
        stats = migrator.migrate_all(args.data_dir, args.dry_run)
        
        # Print results
        print(f"\n=== MIGRATION RESULTS ===")
        print(f"Total files found: {stats['total_files']}")
        print(f"Successful migrations: {stats['successful_migrations']}")
        print(f"Failed migrations: {stats['failed_migrations']}")
        print(f"Skipped files: {stats['skipped_files']}")
        
        if not args.dry_run and stats['successful_migrations'] > 0:
            print(f"\n[SUCCESS] Migration completed successfully!")
            print(f"[HINT] Run 'python migrate_data_to_postgresql.py --verify' to verify the data.")
        elif args.dry_run:
            print(f"\nDry run completed. Run without --dry-run to perform actual migration.")
        
    except KeyboardInterrupt:
        print("\nMigration cancelled by user.")
    except Exception as e:
        print(f"\nMigration failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()