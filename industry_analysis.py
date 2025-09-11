#!/usr/bin/env python3
"""
Industry Analysis Module - AI-powered Industry Sentiment Analysis
A professional-grade industry analysis tool that combines company identification with comprehensive industry sentiment analysis.

FEATURES:
- Automatic company industry classification using Gemini AI
- Industry-specific sentiment analysis with OpenAI GPT models
- Partitioned database storage for optimal performance
- Comprehensive trend analysis and reasoning
- Source attribution and confidence scoring
"""

import warnings
import json
import os
import psycopg2
from typing import Dict, Optional, List
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from database_config import POSTGRES_CONFIG

warnings.filterwarnings('ignore')

# Industry list for classification
INDUSTRY_LIST = [
    "Technology",
    "Semiconductor", 
    "Healthcare",
    "Finance",
    "Retail",
    "Manufacturing",
    "Energy",
    "Consumer Goods",
    "Real Estate",
    "Telecommunications",
    "Utilities",
    "Transportation",
    "Hospitality",
    "Construction",
    "Education",
    "Government",
    "Agriculture",
    "Media & Entertainment",
    "Professional Services",
    "Pharmaceuticals",
    "Biotechnology",
    "Automotive",
    "Aerospace & Defense",
    "Insurance",
    "Food & Beverage",
    "Chemicals",
    "Mining & Metals",
    "Logistics & Shipping",
    "E-commerce",
    "Information Technology Services",
    "Renewable Energy",
    "Travel & Tourism",
    "Nonprofit & NGOs",
    "Sports & Recreation",
    "Fashion & Apparel",
    "Legal Services",
    "Advertising & Marketing",
    "Semiconductor Equipment",
    "Internet & Online Services",
    "Electronics",
    "Luxury Goods"
]

# Static mapping of common stock symbols to company names (for quick lookup)
STOCK_SYMBOL_TO_COMPANY = {
    # Major Tech Stocks
    'AAPL': 'Apple Inc.',
    'MSFT': 'Microsoft Corporation',
    'GOOGL': 'Alphabet Inc.',
    'GOOG': 'Alphabet Inc.',
    'AMZN': 'Amazon.com Inc.',
    'META': 'Meta Platforms Inc.',
    'TSLA': 'Tesla Inc.',
    'NVDA': 'NVIDIA Corporation',
    'NFLX': 'Netflix Inc.',
    
    # Financial Stocks
    'JPM': 'JPMorgan Chase & Co.',
    'BAC': 'Bank of America Corporation',
    'WFC': 'Wells Fargo & Company',
    'GS': 'The Goldman Sachs Group Inc.',
    'MS': 'Morgan Stanley',
    'C': 'Citigroup Inc.',
    'V': 'Visa Inc.',
    'MA': 'Mastercard Incorporated',
    
    # Healthcare & Pharma
    'JNJ': 'Johnson & Johnson',
    'PFE': 'Pfizer Inc.',
    'UNH': 'UnitedHealth Group Incorporated',
    'CVS': 'CVS Health Corporation',
    'ABBV': 'AbbVie Inc.',
    
    # Consumer & Retail
    'WMT': 'Walmart Inc.',
    'HD': 'The Home Depot Inc.',
    'PG': 'The Procter & Gamble Company',
    'KO': 'The Coca-Cola Company',
    'MCD': 'McDonald\'s Corporation',
    'DIS': 'The Walt Disney Company',
    
    # Energy & Utilities
    'XOM': 'Exxon Mobil Corporation',
    'CVX': 'Chevron Corporation',
    
    # Industrial
    'BA': 'The Boeing Company',
    'CAT': 'Caterpillar Inc.',
    'GE': 'General Electric Company',
}


class IndustryAnalyzer:
    """Professional industry analysis class for AI-powered sentiment analysis with database integration"""
    
    def __init__(self, company_symbol: Optional[str] = None, openai_api_key: Optional[str] = None, gemini_api_key: Optional[str] = None):
        """
        Initialize the Industry Analyzer with lazy API client loading
        
        Args:
            company_symbol: Stock symbol for company-specific analysis (optional)
            openai_api_key: OpenAI API key (if not set in environment)
            gemini_api_key: Gemini API key (if not set in environment) 
        """
        self.company_symbol = company_symbol.upper() if company_symbol else None
        self.company_name = None
        self.industry = None
        
        # Store API keys for lazy initialization
        self._openai_api_key = openai_api_key
        self._gemini_api_key = gemini_api_key
        
        # API clients (will be initialized lazily)
        self.openai_client = None
        self.gemini_client = None
        self._openai_initialized = False
        self._gemini_initialized = False
        
        # Initialize database connection (fast operation)
        self.db_connection = None
        self._init_database()
        
        # If a company symbol is provided, identify the company and industry
        if self.company_symbol:
            self._identify_company_info()
    
    def _ensure_openai_client(self):
        """Lazy initialization of OpenAI client"""
        if self._openai_initialized:
            return
        
        print(f"[LAZY LOAD] Initializing OpenAI client...")
        from openai import OpenAI

        # Set up OpenAI
        if self._openai_api_key:
            os.environ["OPENAI_API_KEY"] = self._openai_api_key
        
        if not os.environ.get("OPENAI_API_KEY"):
            raise ValueError("OpenAI API key must be provided either as parameter or environment variable 'OPENAI_API_KEY'")
        
        self.openai_client = OpenAI()
        self._openai_initialized = True
    
    def _ensure_gemini_client(self):
        """Lazy initialization of Gemini client"""
        if self._gemini_initialized:
            return
        from google import genai
        from google.genai import types
        print(f"[LAZY LOAD] Initializing Gemini client...")
        self.gemini_types = types
        # Set up Gemini
        if self._gemini_api_key:
            os.environ["GEMINI_API_KEY"] = self._gemini_api_key
            
        if not os.environ.get("GEMINI_API_KEY"):
            raise ValueError("Gemini API key must be provided either as parameter or environment variable 'GEMINI_API_KEY'")
        
        self.gemini_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        print(self.gemini_types)
        self._gemini_initialized = True
    
    def _init_database(self):
        """Initialize database connection"""
        try:
            print(f"Initializing database connection...")
            self.db_connection = psycopg2.connect(
                host=POSTGRES_CONFIG['host'],
                port=POSTGRES_CONFIG['port'],
                database=POSTGRES_CONFIG['database'],
                user=POSTGRES_CONFIG['username'],
                password=POSTGRES_CONFIG['password']
            )
            print(f"[SUCCESS] Database connection established")
        except Exception as e:
            print(f"[WARNING] Database connection failed: {e}")
            self.db_connection = None
    
    def _get_cached_company_info(self, symbol: str, max_days: int = 30) -> Optional[Dict]:
        """Get cached company info from database if it exists and is recent enough"""
        if not self.db_connection:
            return None
        
        try:
            cur = self.db_connection.cursor()
            
            cur.execute("""
                SELECT * FROM get_company_info(%s, %s)
            """, (symbol.upper(), max_days))
            
            result = cur.fetchone()
            
            if result:
                columns = ['symbol', 'company_name', 'industry', 'needs_update', 'days_old', 'last_verified']
                company_info = dict(zip(columns, result))
                return company_info
            
            return None
            
        except Exception as e:
            print(f"[ERROR] Failed to get cached company info: {e}")
            return None
        finally:
            if cur:
                cur.close()
    
    def _save_company_info_to_cache(self, symbol: str, company_name: str, industry: str) -> bool:
        """Save or update company info in database cache"""
        if not self.db_connection:
            return False
        
        try:
            cur = self.db_connection.cursor()
            
            cur.execute("""
                SELECT upsert_company_info(%s, %s, %s)
            """, (symbol.upper(), company_name, industry))
            
            company_id = cur.fetchone()[0]
            self.db_connection.commit()
            
            print(f"[CACHE] Saved company info for {symbol} (ID: {company_id})")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to save company info to cache: {e}")
            if self.db_connection:
                self.db_connection.rollback()
            return False
        finally:
            if cur:
                cur.close()
    
    def _identify_company_info(self):
        """Identify company name and industry from stock symbol with intelligent caching"""
        if not self.company_symbol:
            return
        
        print(f"[INFO] Identifying company info for {self.company_symbol}...")
        
        # Step 1: Check database cache first
        cached_info = self._get_cached_company_info(self.company_symbol)
        
        if cached_info and not cached_info['needs_update']:
            # Use cached data if it's fresh (less than 30 days old)
            self.company_name = cached_info['company_name']
            self.industry = cached_info['industry']
            print(f"[CACHE HIT] Using cached company info ({cached_info['days_old']} days old)")
            print(f"[TOKEN SAVINGS] Skipped Gemini API call for {self.company_symbol}")
            print(f"[SUCCESS] Company: {self.company_name}")
            print(f"[SUCCESS] Industry: {self.industry}")
            return
        
        # Step 2: Try static lookup for known companies
        static_company_name = STOCK_SYMBOL_TO_COMPANY.get(self.company_symbol)
        
        if static_company_name and cached_info and cached_info['needs_update']:
            # We have static data and cached data is old - update with fresh AI call
            print(f"[CACHE EXPIRED] Cached data is {cached_info['days_old']} days old, updating...")
            company_info = self._generate_company_info(self.company_symbol)
            self.company_name = company_info.get('company_name', static_company_name)
            self.industry = company_info.get('industry')
            
            # Update cache with fresh data
            self._save_company_info_to_cache(self.company_symbol, self.company_name, self.industry)
            
        elif static_company_name and not cached_info:
            # We have static data but no cache - get industry from AI and save to cache
            print(f"[STATIC LOOKUP] Found {static_company_name}, getting industry from AI...")
            company_info = self._generate_company_info(self.company_symbol)
            self.company_name = static_company_name
            self.industry = company_info.get('industry')
            
            # Save to cache for future use
            self._save_company_info_to_cache(self.company_symbol, self.company_name, self.industry)
            
        elif not static_company_name and cached_info and cached_info['needs_update']:
            # No static data, but cached data is old - update with fresh AI call
            print(f"[CACHE EXPIRED] Cached data is {cached_info['days_old']} days old, updating...")
            company_info = self._generate_company_info(self.company_symbol)
            self.company_name = company_info.get('company_name', f'{self.company_symbol} Corporation')
            self.industry = company_info.get('industry')
            
            # Update cache with fresh data
            self._save_company_info_to_cache(self.company_symbol, self.company_name, self.industry)
            
        else:
            # No static data and no cache - use AI and save to cache
            print(f"[NEW SYMBOL] No cached data found, using AI to identify...")
            company_info = self._generate_company_info(self.company_symbol)
            self.company_name = company_info.get('company_name', f'{self.company_symbol} Corporation')
            self.industry = company_info.get('industry')
            
            # Save to cache for future use
            self._save_company_info_to_cache(self.company_symbol, self.company_name, self.industry)
        
        print(f"[SUCCESS] Company: {self.company_name}")
        print(f"[SUCCESS] Industry: {self.industry}")
    
    def _generate_company_info(self, symbol: str) -> Dict:
        """Use Gemini AI to identify company name and industry"""
        try:
            # Ensure Gemini client is initialized
            self._ensure_gemini_client()
            
            contents = [
                self.gemini_types.Content(
                    role="user",
                    parts=[
                        self.gemini_types.Part.from_text(
                            text=f"What industry best fits the company with stock symbol {symbol} from these industries? "
                                 f"Options: [{', '.join(INDUSTRY_LIST)}] "
                                 f"Respond in JSON format: {{'industry': '<string>', 'company_name': '<string>'}}"
                        ),
                    ],
                ),
            ]
            
            generate_content_config = self.gemini_types.GenerateContentConfig(
                thinking_config=self.gemini_types.ThinkingConfig(thinking_budget=0),
                response_mime_type="application/json",
            )

            response_parts = []
            for chunk in self.gemini_client.models.generate_content_stream(
                model="gemini-2.5-flash-lite",
                contents=contents,
                config=generate_content_config,
            ):
                response_parts.append(chunk.text)
            
            full_response = "".join(response_parts)
            return json.loads(full_response.replace("'", '"'))
            
        except Exception as e:
            print(f"[ERROR] Failed to identify company info: {e}")
            return {'industry': 'Technology', 'company_name': f'{symbol} Corporation'}
    
    def analyze_industry(self, industry: Optional[str] = None, target_company_symbol: Optional[str] = None, target_company_name: Optional[str] = None, force_refresh: bool = False, cache_hours: float = 24.0) -> Dict:
        """
        Analyze industry sentiment with comprehensive AI analysis and intelligent caching
        
        Args:
            industry: Industry to analyze (uses instance industry if not provided)
            target_company_symbol: Specific company symbol for context
            target_company_name: Specific company name for context
            force_refresh: If True, bypass cache and force fresh analysis
            cache_hours: Maximum age of cached data in hours (default: 24 hours)
            
        Returns:
            Dictionary containing comprehensive industry analysis
        """
        # Determine which industry to analyze
        analysis_industry = industry or self.industry
        if not analysis_industry:
            raise ValueError("Industry must be provided either in constructor with company_symbol or as parameter")
        
        # Determine company context
        analysis_symbol = target_company_symbol or self.company_symbol
        analysis_company = target_company_name or self.company_name
        
        print(f"[INFO] Starting industry analysis for: {analysis_industry}")
        if analysis_symbol and analysis_company:
            print(f"[INFO] Company context: {analysis_company} ({analysis_symbol})")
        
        # Check for cached data first (unless forced refresh)
        if not force_refresh and self.db_connection:
            print(f"[CACHE] Checking for cached analysis (max age: {cache_hours}h)...")
            cached_analysis = self._get_cached_industry_analysis(analysis_industry, cache_hours)
            
            if cached_analysis:
                print(f"[CACHE HIT] Found cached analysis for {analysis_industry}")
                print(f"[CACHE INFO] Age: {cached_analysis['cache_age_hours']:.1f} hours")
                print(f"[CACHE INFO] Sentiment: {cached_analysis['sentiment_label']} ({cached_analysis['overall_sentiment']:.3f})")
                print(f"[TOKEN SAVINGS] Skipped OpenAI API call - using cached data")
                
                # Update company context if provided and different
                if analysis_symbol and cached_analysis.get('company_symbol') != analysis_symbol:
                    cached_analysis['company_symbol'] = analysis_symbol
                    cached_analysis['company_name'] = analysis_company
                
                return cached_analysis
            else:
                print(f"[CACHE MISS] No recent cached data found, performing fresh analysis...")
        elif force_refresh:
            print(f"[FORCE REFRESH] Bypassing cache, performing fresh analysis...")
        else:
            print(f"[NO CACHE] No database connection, performing fresh analysis...")
        
        # Create analysis prompt for fresh analysis
        sentiment_labels = ["Very Positive", "Positive", "Neutral", "Negative", "Very Negative"]
        format_string = f"""{{
    "industry": "{analysis_industry}",
    "overall_sentiment": <float between -1.0 and 1.0>,
    "sentiment_label": {' | '.join(sentiment_labels)},
    "confidence_score": <float between 0.0 and 1.0>,
    "key_trends": [<array of trend strings>],
    "reasoning": <detailed reasoning string>,
    "sources": [<array of source URLs>]
}}"""
        
        try:
            print(f"[API CALL] Generating fresh analysis using OpenAI...")
            # Ensure OpenAI client is initialized
            self._ensure_openai_client()
            
            # Generate analysis using OpenAI
            response = self.openai_client.responses.create(
                model="gpt-5-nano",
                tools=[{"type": "web_search"}],
                input=f"Analyze the {analysis_industry} industry sentiment and trends. "
                      f"Respond in this exact JSON format: {format_string}"
            )
            
            # Parse the response
            analysis_data = json.loads(response.output_text)
            analysis_data['confidence_score'] = float(analysis_data['confidence_score'])
            analysis_data['overall_sentiment'] = float(analysis_data['overall_sentiment'])
            
            # Add metadata
            analysis_data['analysis_timestamp'] = datetime.now().isoformat()
            analysis_data['company_symbol'] = analysis_symbol
            analysis_data['company_name'] = analysis_company
            analysis_data['cached'] = False  # Mark as fresh analysis
            
            # Save to database if available
            if self.db_connection:
                db_id = self._save_to_database(analysis_data, analysis_symbol, analysis_company)
                if db_id:
                    analysis_data['database_id'] = db_id
                    print(f"[SUCCESS] Fresh analysis saved to database (ID: {db_id})")
                else:
                    print(f"[WARNING] Failed to save to database")
            
            # Save to file as backup
            #self._save_to_file(analysis_data, analysis_symbol or 'general')
            
            print(f"[SUCCESS] Industry analysis completed using fresh API data")
            print(f"[RESULT] {analysis_industry} - {analysis_data['sentiment_label']} (confidence: {analysis_data['confidence_score']:.2f})")
            
            return analysis_data
            
        except Exception as e:
            print(f"[ERROR] Industry analysis failed: {e}")
            raise
    
    def _save_to_database(self, data: Dict, company_symbol: Optional[str], company_name: Optional[str]) -> Optional[int]:
        """Save analysis data to the partitioned database table"""
        if not self.db_connection:
            return None
        
        try:
            cur = self.db_connection.cursor()
            
            # Prepare data for insertion
            key_trends_json = json.dumps(data['key_trends'])
            sources_json = json.dumps(data['sources'])
            
            # Insert data using the function
            cur.execute("""
                SELECT insert_industry_analysis(%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                data['industry'],
                company_symbol,
                company_name,
                data['overall_sentiment'],
                data['sentiment_label'],
                data['confidence_score'],
                key_trends_json,
                data['reasoning'],
                sources_json
            ))
            
            inserted_id = cur.fetchone()[0]
            self.db_connection.commit()
            
            return inserted_id
            
        except Exception as e:
            print(f"[ERROR] Database save failed: {e}")
            if self.db_connection:
                self.db_connection.rollback()
            return None
        finally:
            if cur:
                cur.close()
    
    def _save_to_file(self, data: Dict, identifier: str):
        """Save analysis data to JSON file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"industry_analysis_{identifier}_{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            print(f"[INFO] Analysis saved to file: {filename}")
            
        except Exception as e:
            print(f"[WARNING] Failed to save to file: {e}")
    
    def get_recent_industry_analysis(self, industry: str, limit: int = 10) -> List[Dict]:
        """Get recent analysis for a specific industry from database"""
        if not self.db_connection:
            print("[WARNING] No database connection available")
            return []
        
        try:
            cur = self.db_connection.cursor()
            
            cur.execute("""
                SELECT * FROM get_recent_industry_analysis(%s, %s)
            """, (industry, limit))
            
            results = cur.fetchall()
            
            # Convert to dictionaries
            columns = [desc[0] for desc in cur.description]
            analyses = []
            
            for row in results:
                analysis = dict(zip(columns, row))
                # Parse JSON fields (handle both string and already-parsed data)
                if analysis.get('key_trends'):
                    if isinstance(analysis['key_trends'], str):
                        analysis['key_trends'] = json.loads(analysis['key_trends'])
                if analysis.get('sources'):
                    if isinstance(analysis['sources'], str):
                        analysis['sources'] = json.loads(analysis['sources'])
                analyses.append(analysis)
            
            return analyses
            
        except Exception as e:
            print(f"[ERROR] Failed to get recent analysis: {e}")
            return []
        finally:
            if cur:
                cur.close()
    
    def _get_cached_industry_analysis(self, industry: str, max_hours: float = 24.0) -> Optional[Dict]:
        """Get cached industry analysis if it exists and is recent enough"""
        if not self.db_connection:
            return None
        
        try:
            cur = self.db_connection.cursor()
            
            # Query for recent analysis within the specified hours
            cur.execute("""
                SELECT id, industry, company_symbol, company_name, overall_sentiment, 
                       sentiment_label, confidence_score, key_trends, reasoning, sources, 
                       created_at, updated_at,
                       EXTRACT(EPOCH FROM (NOW() - created_at))/3600 AS hours_old
                FROM industry_analysis_partitioned 
                WHERE industry = %s 
                AND created_at > NOW() - INTERVAL '%s hours'
                ORDER BY created_at DESC 
                LIMIT 1
            """, (industry, max_hours))
            
            result = cur.fetchone()
            
            if result:
                columns = [desc[0] for desc in cur.description]
                analysis = dict(zip(columns, result))
                
                # Parse JSON fields
                if analysis.get('key_trends'):
                    if isinstance(analysis['key_trends'], str):
                        analysis['key_trends'] = json.loads(analysis['key_trends'])
                if analysis.get('sources'):
                    if isinstance(analysis['sources'], str):
                        analysis['sources'] = json.loads(analysis['sources'])
                
                # Add cache metadata
                analysis['cached'] = True
                analysis['cache_age_hours'] = float(analysis['hours_old'])
                analysis['analysis_timestamp'] = analysis['created_at'].isoformat()
                
                return analysis
            
            return None
            
        except Exception as e:
            print(f"[ERROR] Failed to get cached analysis: {e}")
            return None
        finally:
            if cur:
                cur.close()
    
    def get_industry_overview(self) -> Dict:
        """Get overview of all industries with latest analysis data"""
        if not self.db_connection:
            print("[WARNING] No database connection available")
            return {}
        
        try:
            cur = self.db_connection.cursor()
            
            cur.execute("""
                SELECT * FROM latest_industry_analysis ORDER BY industry
            """)
            
            results = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            
            overview = {}
            for row in results:
                analysis = dict(zip(columns, row))
                industry = analysis['industry']
                overview[industry] = {
                    'latest_sentiment': analysis['sentiment_label'],
                    'latest_score': float(analysis['overall_sentiment']),
                    'confidence': float(analysis['confidence_score']),
                    'last_updated': analysis['created_at'].isoformat() if analysis['created_at'] else None,
                    'company_context': f"{analysis['company_name']} ({analysis['company_symbol']})" if analysis['company_symbol'] else None
                }
            
            return overview
            
        except Exception as e:
            print(f"[ERROR] Failed to get industry overview: {e}")
            return {}
        finally:
            if cur:
                cur.close()
    
    @staticmethod
    def get_supported_industries() -> List[str]:
        """Get list of supported industries"""
        return INDUSTRY_LIST.copy()
    
    @staticmethod
    def get_supported_companies() -> Dict[str, str]:
        """Get dictionary of supported company symbols and names"""
        return STOCK_SYMBOL_TO_COMPANY.copy()
    
    def get_company_cache_status(self) -> List[Dict]:
        """Get status of all cached companies"""
        if not self.db_connection:
            print("[WARNING] No database connection available")
            return []
        
        try:
            cur = self.db_connection.cursor()
            
            cur.execute("SELECT * FROM company_cache_status")
            
            results = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            
            companies = []
            for row in results:
                company = dict(zip(columns, row))
                companies.append(company)
            
            return companies
            
        except Exception as e:
            print(f"[ERROR] Failed to get company cache status: {e}")
            return []
        finally:
            if cur:
                cur.close()
    
    def get_companies_needing_update(self, max_days: int = 30) -> List[Dict]:
        """Get companies that need their info updated"""
        if not self.db_connection:
            print("[WARNING] No database connection available")
            return []
        
        try:
            cur = self.db_connection.cursor()
            
            cur.execute("SELECT * FROM get_companies_needing_update(%s)", (max_days,))
            
            results = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            
            companies = []
            for row in results:
                company = dict(zip(columns, row))
                companies.append(company)
            
            return companies
            
        except Exception as e:
            print(f"[ERROR] Failed to get companies needing update: {e}")
            return []
        finally:
            if cur:
                cur.close()
    
    def close(self):
        """Close database connection"""
        if self.db_connection:
            self.db_connection.close()
            self.db_connection = None
            print("[INFO] Database connection closed")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


def main():
    """Command-line interface for industry analysis"""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='AI-Powered Industry Sentiment Analysis')
    parser.add_argument('--symbol', '-s', help='Company stock symbol (e.g., AAPL)')
    parser.add_argument('--industry', '-i', help='Industry to analyze directly')
    parser.add_argument('--recent', '-r', type=int, default=5, help='Show recent analyses (default: 5)')
    parser.add_argument('--overview', action='store_true', help='Show overview of all industries')
    parser.add_argument('--list-industries', action='store_true', help='List supported industries')
    parser.add_argument('--list-companies', action='store_true', help='List supported companies')
    parser.add_argument('--company-cache', action='store_true', help='Show company cache status')
    parser.add_argument('--force-refresh', action='store_true', help='Force fresh analysis, bypass cache')
    parser.add_argument('--cache-hours', type=float, default=24.0, help='Max cache age in hours (default: 24)')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    print("STARTING")
    # Handle list commands
    if args.list_industries:
        industries = IndustryAnalyzer.get_supported_industries()
        if args.json:
            print(json.dumps(industries, indent=2))
        else:
            print("Supported Industries:")
            for industry in industries:
                print(f"  - {industry}")
        return
    
    if args.list_companies:
        companies = IndustryAnalyzer.get_supported_companies()
        if args.json:
            print(json.dumps(companies, indent=2))
        else:
            print("Supported Companies:")
            for symbol, name in companies.items():
                print(f"  {symbol}: {name}")
        return
    
    if args.company_cache:
        try:
            analyzer = IndustryAnalyzer()
            cache_status = analyzer.get_company_cache_status()
            
            if args.json:
                print(json.dumps(cache_status, indent=2, default=str))
            else:
                print("Company Cache Status:")
                print(f"Total cached companies: {len(cache_status)}")
                
                if cache_status:
                    fresh_count = sum(1 for c in cache_status if c['status'] == 'FRESH')
                    aging_count = sum(1 for c in cache_status if c['status'] == 'AGING')
                    needs_update_count = sum(1 for c in cache_status if c['status'] == 'NEEDS_UPDATE')
                    
                    print(f"  Fresh (< 14 days): {fresh_count}")
                    print(f"  Aging (14-30 days): {aging_count}")
                    print(f"  Needs Update (> 30 days): {needs_update_count}")
                    print()
                    
                    # Show some examples
                    print("Sample entries:")
                    for company in cache_status[:10]:
                        status_indicator = "[OK]" if company['status'] == 'FRESH' else "[AGING]" if company['status'] == 'AGING' else "[UPDATE]"
                        print(f"  {status_indicator} {company['symbol']}: {company['company_name']} ({company['industry']}) - {company['days_old']} days old")
                        
                    if len(cache_status) > 10:
                        print(f"  ... and {len(cache_status) - 10} more")
                else:
                    print("  No companies cached yet")
                    
            analyzer.close()
        except Exception as e:
            print(f"Error showing company cache: {e}")
        return
    
    # Initialize analyzer
    try:
        if args.symbol:
            analyzer = IndustryAnalyzer(company_symbol=args.symbol)
        else:
            analyzer = IndustryAnalyzer()
    except ValueError as e:
        print(f"[ERROR] {e}")
        print("Please set OPENAI_API_KEY and GEMINI_API_KEY environment variables")
        sys.exit(1)
    
    with analyzer:
        try:
            if args.overview:
                # Show industry overview
                overview = analyzer.get_industry_overview()
                if args.json:
                    print(json.dumps(overview, indent=2, default=str))
                else:
                    print("\n=== INDUSTRY OVERVIEW ===")
                    for industry, data in overview.items():
                        print(f"{industry}: {data['latest_sentiment']} ({data['latest_score']:.2f})")
                        if data['company_context']:
                            print(f"  Context: {data['company_context']}")
                        if data['last_updated']:
                            print(f"  Updated: {data['last_updated']}")
                        print()
            
            elif args.industry:
                # Analyze specific industry
                results = analyzer.analyze_industry(
                    industry=args.industry, 
                    force_refresh=args.force_refresh, 
                    cache_hours=args.cache_hours
                )
                
                if args.json:
                    print(json.dumps(results, indent=2, default=str))
                else:
                    print(f"\n=== INDUSTRY ANALYSIS: {results['industry']} ===")
                    print(f"Overall Sentiment: {results['sentiment_label']}")
                    print(f"Sentiment Score: {results['overall_sentiment']:.3f}")
                    print(f"Confidence: {results['confidence_score']:.2f}")
                    print(f"\nKey Trends:")
                    for trend in results['key_trends']:
                        print(f"  • {trend}")
                    print(f"\nReasoning: {results['reasoning']}")
                    
                # Show recent analyses
                recent = analyzer.get_recent_industry_analysis(args.industry, args.recent)
                if recent:
                    print(f"\n=== RECENT ANALYSES ({len(recent)}) ===")
                    for analysis in recent:
                        print(f"{analysis['created_at']}: {analysis['sentiment_label']} ({analysis['overall_sentiment']:.2f})")
            
            elif args.symbol and analyzer.industry:
                # Analyze industry for the company
                results = analyzer.analyze_industry(
                    force_refresh=args.force_refresh, 
                    cache_hours=args.cache_hours
                )
                
                if args.json:
                    print(json.dumps(results, indent=2, default=str))
                else:
                    print(f"\n=== INDUSTRY ANALYSIS FOR {analyzer.company_name} ({args.symbol}) ===")
                    print(f"Industry: {results['industry']}")
                    print(f"Overall Sentiment: {results['sentiment_label']}")
                    print(f"Sentiment Score: {results['overall_sentiment']:.3f}")
                    print(f"Confidence: {results['confidence_score']:.2f}")
                    print(f"\nKey Trends:")
                    for trend in results['key_trends']:
                        print(f"  • {trend}")
                    print(f"\nReasoning: {results['reasoning']}")
            
            else:
                print("Please specify --symbol, --industry, --overview, or use --help for options")
                
        except Exception as e:
            print(f"[ERROR] Analysis failed: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()