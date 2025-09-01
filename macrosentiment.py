import requests
import pandas as pd
from datetime import datetime, timedelta
import json
import re
from typing import Dict, List, Optional, Tuple, Set
from urllib.parse import quote
import time
import logging
from dataclasses import dataclass, field
import os
import pickle
from functools import wraps
from collections import defaultdict, Counter
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MacroEvent:
    date: str
    title: str
    source: str
    tone: float
    goldstein_scale: float
    num_mentions: int
    event_type: str
    countries: List[str]
    themes: List[str]
    impact_score: float
    url: str = ""
    language: str = ""
    word_count: int = 0
    # Enhanced fields for better analysis
    sector_relevance_scores: Dict[str, float] = field(default_factory=dict)
    content_quality_score: float = 0.0
    event_urgency: str = "medium"  # low, medium, high, critical
    geographic_impact: List[str] = field(default_factory=list)

class EnhancedSectorClassifier:
    """Advanced sector classification with contextual understanding"""
    
    SECTOR_MAP = {
        # Technology - Expanded with more modern companies
        'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOGL': 'Technology', 'GOOG': 'Technology',
        'META': 'Technology', 'NVDA': 'Technology', 'TSLA': 'Technology', 'NFLX': 'Technology',
        'AMZN': 'Technology', 'ORCL': 'Technology', 'CRM': 'Technology', 'ADBE': 'Technology',
        'INTC': 'Technology', 'AMD': 'Technology', 'QCOM': 'Technology', 'AVGO': 'Technology',
        'NOW': 'Technology', 'SNOW': 'Technology', 'PLTR': 'Technology', 'ZM': 'Technology',
        
        # Financial
        'JPM': 'Financial', 'BAC': 'Financial', 'WFC': 'Financial', 'GS': 'Financial',
        'MS': 'Financial', 'C': 'Financial', 'AXP': 'Financial', 'BLK': 'Financial',
        'SCHW': 'Financial', 'BRK.B': 'Financial', 'BRK.A': 'Financial', 'V': 'Financial',
        'MA': 'Financial', 'PYPL': 'Financial',
        
        # Healthcare - Expanded
        'JNJ': 'Healthcare', 'UNH': 'Healthcare', 'PFE': 'Healthcare', 'ABBV': 'Healthcare',
        'LLY': 'Healthcare', 'TMO': 'Healthcare', 'DHR': 'Healthcare', 'BMY': 'Healthcare',
        'MRK': 'Healthcare', 'CVS': 'Healthcare', 'ABT': 'Healthcare', 'MRNA': 'Healthcare',
        'GILD': 'Healthcare', 'REGN': 'Healthcare',
        
        # Energy
        'XOM': 'Energy', 'CVX': 'Energy', 'COP': 'Energy', 'SLB': 'Energy',
        'EOG': 'Energy', 'MPC': 'Energy', 'PSX': 'Energy', 'VLO': 'Energy',
        'ENPH': 'Energy', 'NEE': 'Energy',
        
        # Consumer Discretionary
        'HD': 'Consumer Discretionary', 'MCD': 'Consumer Discretionary', 'NKE': 'Consumer Discretionary',
        'SBUX': 'Consumer Discretionary', 'TGT': 'Consumer Discretionary', 'LOW': 'Consumer Discretionary',
        'AMZN': 'Consumer Discretionary',  # Note: Amazon spans multiple sectors
        
        # Consumer Staples
        'PG': 'Consumer Staples', 'KO': 'Consumer Staples', 'PEP': 'Consumer Staples',
        'WMT': 'Consumer Staples', 'COST': 'Consumer Staples', 'CL': 'Consumer Staples',
        
        # Industrial
        'BA': 'Industrial', 'CAT': 'Industrial', 'GE': 'Industrial', 'MMM': 'Industrial',
        'UPS': 'Industrial', 'FDX': 'Industrial', 'RTX': 'Industrial', 'HON': 'Industrial',
        
        # Materials
        'LIN': 'Materials', 'APD': 'Materials', 'ECL': 'Materials', 'FCX': 'Materials',
        'NEM': 'Materials', 'DOW': 'Materials',
        
        # Utilities
        'NEE': 'Utilities', 'DUK': 'Utilities', 'SO': 'Utilities', 'EXC': 'Utilities',
        
        # Real Estate
        'AMT': 'Real Estate', 'PLD': 'Real Estate', 'CCI': 'Real Estate', 'EQIX': 'Real Estate',
        
        # Communications
        'VZ': 'Communications', 'T': 'Communications', 'CMCSA': 'Communications', 'DIS': 'Communications',
        'NFLX': 'Communications'  # Netflix spans tech and communications
    }
    
    # Enhanced sector definitions with contextual patterns
    SECTOR_CONTEXTS = {
        'Technology': {
            'primary_indicators': [
                'artificial intelligence', 'machine learning', 'cloud computing', 'software', 
                'semiconductor', 'chip', 'processor', 'data center', 'cybersecurity',
                'blockchain', 'cryptocurrency', 'fintech', 'saas', 'platform', 'api'
            ],
            'secondary_indicators': [
                'innovation', 'startup', 'venture capital', 'digital transformation',
                'automation', 'robotics', 'internet of things', 'iot', '5g', 'quantum'
            ],
            'impact_factors': [
                'regulation', 'privacy', 'antitrust', 'patent', 'r&d spending',
                'talent acquisition', 'supply chain disruption', 'chip shortage'
            ],
            'negative_patterns': [
                'biotech', 'pharmaceutical', 'medical device', 'healthcare tech'  # These should go to healthcare
            ]
        },
        'Financial': {
            'primary_indicators': [
                'interest rate', 'monetary policy', 'federal reserve', 'banking',
                'lending', 'credit', 'mortgage', 'investment', 'trading',
                'insurance', 'asset management', 'wealth management'
            ],
            'secondary_indicators': [
                'inflation', 'yield curve', 'liquidity', 'capital adequacy',
                'stress test', 'dodd-frank', 'basel', 'compliance'
            ],
            'impact_factors': [
                'economic outlook', 'recession risk', 'unemployment', 'gdp growth',
                'consumer confidence', 'housing market', 'default rates'
            ]
        },
        'Healthcare': {
            'primary_indicators': [
                'pharmaceutical', 'biotech', 'clinical trial', 'fda approval',
                'drug development', 'vaccine', 'therapeutic', 'medical device',
                'diagnostics', 'hospital', 'healthcare'
            ],
            'secondary_indicators': [
                'aging population', 'pandemic', 'epidemic', 'public health',
                'medicare', 'medicaid', 'health insurance', 'telehealth'
            ],
            'impact_factors': [
                'regulatory approval', 'patent cliff', 'pricing pressure',
                'healthcare reform', 'drug pricing legislation'
            ]
        },
        'Energy': {
            'primary_indicators': [
                'oil price', 'natural gas', 'petroleum', 'refining', 'drilling',
                'renewable energy', 'solar', 'wind', 'hydroelectric', 'nuclear',
                'battery', 'energy storage', 'electric vehicle', 'ev'
            ],
            'secondary_indicators': [
                'opec', 'pipeline', 'shale', 'fracking', 'lng', 'carbon capture',
                'grid', 'transmission', 'distribution'
            ],
            'impact_factors': [
                'climate policy', 'carbon tax', 'esg investing', 'geopolitical risk',
                'commodity prices', 'weather patterns', 'energy transition'
            ]
        },
        'Consumer Discretionary': {
            'primary_indicators': [
                'consumer spending', 'retail sales', 'e-commerce', 'omnichannel',
                'restaurant', 'hospitality', 'travel', 'tourism', 'automotive',
                'luxury goods', 'apparel', 'entertainment'
            ],
            'secondary_indicators': [
                'disposable income', 'consumer confidence', 'unemployment rate',
                'gasoline prices', 'housing wealth effect'
            ],
            'impact_factors': [
                'economic cycle', 'seasonal trends', 'supply chain', 'labor costs',
                'inflation', 'interest rates', 'demographic shifts'
            ]
        },
        'Consumer Staples': {
            'primary_indicators': [
                'food and beverage', 'grocery', 'packaged goods', 'household products',
                'personal care', 'tobacco', 'agriculture', 'commodity'
            ],
            'secondary_indicators': [
                'private label', 'brand loyalty', 'distribution', 'shelf space'
            ],
            'impact_factors': [
                'commodity inflation', 'weather', 'trade policy', 'currency',
                'emerging markets', 'health trends'
            ]
        },
        'Industrial': {
            'primary_indicators': [
                'manufacturing', 'aerospace', 'defense', 'construction', 'infrastructure',
                'machinery', 'equipment', 'transportation', 'logistics', 'freight'
            ],
            'secondary_indicators': [
                'capital expenditure', 'industrial production', 'capacity utilization',
                'order backlog', 'lead times'
            ],
            'impact_factors': [
                'economic growth', 'government spending', 'trade policy',
                'raw material costs', 'labor availability', 'technology disruption'
            ]
        },
        'Materials': {
            'primary_indicators': [
                'mining', 'metals', 'chemicals', 'steel', 'aluminum', 'copper',
                'gold', 'silver', 'rare earth', 'lithium', 'paper', 'packaging'
            ],
            'secondary_indicators': [
                'commodity prices', 'supply and demand', 'inventory levels',
                'production capacity', 'exploration'
            ],
            'impact_factors': [
                'global growth', 'china demand', 'infrastructure spending',
                'environmental regulations', 'trade disputes', 'weather'
            ]
        },
        'Utilities': {
            'primary_indicators': [
                'electric utility', 'power generation', 'transmission', 'distribution',
                'water utility', 'gas utility', 'renewable energy'
            ],
            'secondary_indicators': [
                'rate regulation', 'capacity planning', 'grid modernization',
                'energy efficiency', 'demand response'
            ],
            'impact_factors': [
                'regulatory environment', 'weather', 'commodity prices',
                'interest rates', 'environmental policy'
            ]
        },
        'Real Estate': {
            'primary_indicators': [
                'commercial real estate', 'residential real estate', 'reit',
                'property management', 'development', 'construction'
            ],
            'secondary_indicators': [
                'occupancy rates', 'rental rates', 'cap rates', 'noi'
            ],
            'impact_factors': [
                'interest rates', 'economic growth', 'demographics',
                'zoning', 'tax policy', 'remote work trends'
            ]
        },
        'Communications': {
            'primary_indicators': [
                'telecommunications', 'wireless', 'broadband', 'cable', 'satellite',
                'media', 'broadcasting', 'streaming', 'content', 'advertising'
            ],
            'secondary_indicators': [
                'subscriber growth', 'arpu', 'churn', 'spectrum auction',
                'cord cutting', 'content costs'
            ],
            'impact_factors': [
                'technology evolution', 'regulatory changes', 'competition',
                'content wars', 'net neutrality', '5g deployment'
            ]
        }
    }
    
    @classmethod
    def get_sector(cls, symbol: str) -> str:
        """Get sector for a given stock symbol"""
        return cls.SECTOR_MAP.get(symbol.upper(), 'Unknown')
    
    @classmethod
    def calculate_sector_relevance_scores(cls, title: str, content: str = "") -> Dict[str, float]:
        """Calculate relevance scores for all sectors based on contextual analysis"""
        text = (title + " " + content).lower()
        sector_scores = {}
        
        for sector, context in cls.SECTOR_CONTEXTS.items():
            score = 0.0
            
            # Primary indicators carry more weight
            primary_matches = sum(1 for indicator in context['primary_indicators'] 
                                if indicator in text)
            score += primary_matches * 3.0
            
            # Secondary indicators carry medium weight
            secondary_matches = sum(1 for indicator in context['secondary_indicators'] 
                                  if indicator in text)
            score += secondary_matches * 1.5
            
            # Impact factors carry lower weight but still relevant
            impact_matches = sum(1 for factor in context['impact_factors'] 
                               if factor in text)
            score += impact_matches * 1.0
            
            # Penalize for negative patterns (wrong sector classification)
            if 'negative_patterns' in context:
                negative_matches = sum(1 for pattern in context['negative_patterns'] 
                                     if pattern in text)
                score -= negative_matches * 2.0
            
            # Contextual bonuses
            score = cls._apply_contextual_bonuses(text, sector, score)
            
            sector_scores[sector] = max(0.0, score)  # Ensure non-negative scores
        
        return sector_scores
    
    @classmethod
    def _apply_contextual_bonuses(cls, text: str, sector: str, base_score: float) -> float:
        """Apply sector-specific contextual bonuses"""
        score = base_score
        
        # Technology sector bonuses
        if sector == 'Technology':
            if 'earnings' in text and any(term in text for term in ['software', 'cloud', 'ai', 'tech']):
                score *= 1.2
            if 'regulation' in text and any(term in text for term in ['data', 'privacy', 'antitrust']):
                score *= 1.3
        
        # Financial sector bonuses
        elif sector == 'Financial':
            if 'fed' in text or 'federal reserve' in text:
                score *= 1.5
            if 'earnings' in text and any(term in text for term in ['bank', 'credit', 'loan']):
                score *= 1.2
        
        # Healthcare sector bonuses
        elif sector == 'Healthcare':
            if 'fda' in text and any(term in text for term in ['approval', 'trial', 'drug']):
                score *= 1.4
            if 'pandemic' in text or 'epidemic' in text:
                score *= 1.3
        
        # Energy sector bonuses
        elif sector == 'Energy':
            if 'opec' in text or 'oil price' in text:
                score *= 1.4
            if 'climate' in text and any(term in text for term in ['policy', 'regulation', 'carbon']):
                score *= 1.2
        
        return score
    
    @classmethod
    def get_primary_sector(cls, relevance_scores: Dict[str, float]) -> str:
        """Get the primary sector based on relevance scores"""
        if not relevance_scores or all(score == 0 for score in relevance_scores.values()):
            return 'Unknown'
        
        return max(relevance_scores.items(), key=lambda x: x[1])[0]

class EnhancedContentFilter:
    """Advanced content filtering with multi-layered analysis"""
    
    def __init__(self):
        # High-quality financial news domains with reliability scores
        self.trusted_domains = {
            'reuters.com': 1.0, 'bloomberg.com': 1.0, 'wsj.com': 1.0,
            'ft.com': 0.95, 'cnbc.com': 0.9, 'marketwatch.com': 0.9,
            'finance.yahoo.com': 0.85, 'businessinsider.com': 0.8,
            'forbes.com': 0.85, 'economist.com': 0.95, 'barrons.com': 0.9,
            'seekingalpha.com': 0.75, 'morningstar.com': 0.8, 'thestreet.com': 0.7
        }
        
        # Patterns that indicate low-quality or irrelevant content
        self.exclusion_patterns = [
            # Technical/support content
            r'update your browser|support\.google|sites\.google|help\.|tutorial',
            r'user guide|how to|404|page not found|error|login|sign in',
            
            # Entertainment/lifestyle content
            r'movie|film|celebrity|trailer|entertainment|gaming|recipe',
            r'wedding|aisle|lifestyle|health tip|personal story',
            
            # Local news that doesn't affect markets
            r'local news|community|school district|high school|arrested after',
            r'disappearance|cult-like|paralyzed|breaking bones',
            
            # Weather unless it's severe/economic impact
            r'^weather\s|weather forecast(?!\s+affect)',
            
            # Sports unless it's business-related
            r'sports score|game result(?!.*revenue|.*earnings)',
        ]
        
        # Patterns that indicate high business relevance
        self.inclusion_patterns = [
            r'earnings|revenue|profit|loss|guidance|outlook',
            r'merger|acquisition|ipo|bankruptcy|restructuring',
            r'fed|federal reserve|interest rate|inflation|gdp',
            r'stock|shares|trading|investor|market|nasdaq|nyse',
            r'ceo|cfo|executive|board|corporate|regulation|sec',
            r'supply chain|commodity|trade war|tariff|sanctions'
        ]
    
    def evaluate_content_quality(self, title: str, url: str, content: str = "") -> float:
        """Evaluate content quality using multiple criteria"""
        quality_score = 0.0
        text = (title + " " + content).lower()
        
        # 1. Source reliability (30% of score)
        source_score = self._evaluate_source_quality(url)
        quality_score += source_score * 0.3
        
        # 2. Content relevance (40% of score)
        relevance_score = self._evaluate_content_relevance(text)
        quality_score += relevance_score * 0.4
        
        # 3. Title quality (20% of score)
        title_score = self._evaluate_title_quality(title)
        quality_score += title_score * 0.2
        
        # 4. Content depth (10% of score)
        depth_score = self._evaluate_content_depth(text)
        quality_score += depth_score * 0.1
        
        return min(1.0, quality_score)  # Cap at 1.0
    
    def _evaluate_source_quality(self, url: str) -> float:
        """Evaluate the quality of the news source"""
        url_lower = url.lower()
        
        # Check against trusted domains
        for domain, reliability in self.trusted_domains.items():
            if domain in url_lower:
                return reliability
        
        # Check for other financial indicators in domain
        financial_indicators = ['invest', 'market', 'finance', 'money', 'stock', 'business']
        if any(indicator in url_lower for indicator in financial_indicators):
            return 0.6
        
        # Check for news indicators
        news_indicators = ['news', 'times', 'post', 'tribune', 'journal', 'gazette']
        if any(indicator in url_lower for indicator in news_indicators):
            return 0.5
        
        # Unknown source
        return 0.3
    
    def _evaluate_content_relevance(self, text: str) -> float:
        """Evaluate how relevant the content is to business/finance"""
        relevance_score = 0.0
        
        # Check for exclusion patterns (reduce score)
        for pattern in self.exclusion_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                relevance_score -= 0.3
        
        # Check for inclusion patterns (increase score)
        inclusion_matches = 0
        for pattern in self.inclusion_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                inclusion_matches += 1
        
        relevance_score += min(1.0, inclusion_matches * 0.2)
        
        # Check for financial terminology density
        financial_terms = [
            'financial', 'economic', 'business', 'corporate', 'industry',
            'company', 'enterprise', 'commercial', 'market', 'investment'
        ]
        
        term_count = sum(1 for term in financial_terms if term in text)
        relevance_score += min(0.3, term_count * 0.05)
        
        return max(0.0, min(1.0, relevance_score))
    
    def _evaluate_title_quality(self, title: str) -> float:
        """Evaluate the quality of the article title"""
        title_lower = title.lower()
        quality_score = 0.5  # Base score
        
        # Optimal title length
        word_count = len(title.split())
        if 8 <= word_count <= 15:  # Optimal range for news headlines
            quality_score += 0.2
        elif word_count < 4 or word_count > 20:
            quality_score -= 0.2
        
        # Check for clickbait patterns (negative)
        clickbait_patterns = [
            r'you won\'t believe', r'shocking', r'amazing', r'incredible',
            r'this will blow your mind', r'must see', r'viral'
        ]
        
        for pattern in clickbait_patterns:
            if re.search(pattern, title_lower):
                quality_score -= 0.3
        
        # Check for professional news patterns (positive)
        professional_patterns = [
            r'reports?', r'announces?', r'reveals?', r'shows?',
            r'according to', r'data shows?', r'study finds?'
        ]
        
        for pattern in professional_patterns:
            if re.search(pattern, title_lower):
                quality_score += 0.2
                break
        
        # Check for specific numbers/data (positive)
        if re.search(r'\d+%|\$[\d,]+|Q[1-4]|\d+\s*(billion|million)', title):
            quality_score += 0.1
        
        return max(0.0, min(1.0, quality_score))
    
    def _evaluate_content_depth(self, text: str) -> float:
        """Evaluate the depth and substantiveness of content"""
        if not text:
            return 0.0
        
        depth_score = 0.5  # Base score
        
        # Word count indicates depth
        word_count = len(text.split())
        if word_count > 200:
            depth_score += 0.3
        elif word_count > 100:
            depth_score += 0.2
        elif word_count < 50:
            depth_score -= 0.2
        
        # Check for analytical language
        analytical_terms = [
            'analysis', 'forecast', 'projection', 'estimate', 'outlook',
            'impact', 'consequence', 'implication', 'trend', 'pattern'
        ]
        
        analytical_count = sum(1 for term in analytical_terms if term in text)
        depth_score += min(0.2, analytical_count * 0.05)
        
        return max(0.0, min(1.0, depth_score))

def rate_limit(calls_per_minute=30):
    """Enhanced rate limiting decorator with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not hasattr(wrapper, 'last_calls'):
                wrapper.last_calls = []
                wrapper.consecutive_failures = 0
            
            now = time.time()
            # Remove calls older than 1 minute
            wrapper.last_calls = [call_time for call_time in wrapper.last_calls if now - call_time < 60]
            
            # Dynamic rate limiting based on failures
            effective_limit = max(5, calls_per_minute - wrapper.consecutive_failures * 2)
            
            # If we've hit the limit, wait
            if len(wrapper.last_calls) >= effective_limit:
                sleep_time = 60 - (now - wrapper.last_calls[0]) + 1
                logger.info(f"Rate limit reached, sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)
                wrapper.last_calls = []
            
            # Record this call
            wrapper.last_calls.append(now)
            
            try:
                result = func(*args, **kwargs)
                wrapper.consecutive_failures = 0  # Reset on success
                return result
            except Exception as e:
                wrapper.consecutive_failures += 1
                raise e
                
        return wrapper
    return decorator

class EnhancedGDELTAnalyzer:
    """Enhanced GDELT analyzer with improved filtering and classification"""
    
    def __init__(self):
        self.base_url = "https://api.gdeltproject.org/api/v2"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive'
        })
        self.request_delay = 3
        self.max_retries = 3
        self.content_filter = EnhancedContentFilter()
        self.sector_classifier = EnhancedSectorClassifier()
    
    @rate_limit(calls_per_minute=15)
    def get_sector_specific_events(self, 
                                  sector: str,
                                  days_back: int = 7,
                                  min_quality_score: float = 0.6) -> List[MacroEvent]:
        """Get events specifically relevant to a sector using enhanced filtering"""
        try:
            # Get sector context for targeted queries
            sector_context = self.sector_classifier.SECTOR_CONTEXTS.get(sector, {})
            primary_indicators = sector_context.get('primary_indicators', [])
            
            all_events = []
            
            # Phase 1: Broad sector-specific search
            if primary_indicators:
                # Use top 3 most important indicators
                for indicator in primary_indicators[:3]:
                    events = self._fetch_events_by_theme(indicator, days_back)
                    all_events.extend(events)
                    time.sleep(self.request_delay)
                    
                    if len(all_events) > 100:  # Sufficient data
                        break
            
            # Phase 2: General financial news with sector filtering
            general_events = self._fetch_general_financial_events(days_back)
            all_events.extend(general_events)
            
            # Phase 3: Enhanced processing and filtering
            processed_events = []
            for event in all_events:
                # Calculate sector relevance scores
                event.sector_relevance_scores = self.sector_classifier.calculate_sector_relevance_scores(
                    event.title, ""
                )
                
                # Calculate content quality score
                event.content_quality_score = self.content_filter.evaluate_content_quality(
                    event.title, event.url
                )
                
                # Only include events that meet quality and relevance thresholds
                sector_score = event.sector_relevance_scores.get(sector, 0.0)
                if (event.content_quality_score >= min_quality_score and 
                    sector_score > 0.0):
                    
                    # Enhanced impact scoring
                    event.impact_score = self._calculate_enhanced_impact_score(
                        event, sector_score
                    )
                    
                    # Classify event urgency
                    event.event_urgency = self._classify_event_urgency(event)
                    
                    processed_events.append(event)
            
            # Remove duplicates based on title similarity
            unique_events = self._remove_duplicate_events(processed_events)
            
            # Sort by relevance and quality
            return sorted(unique_events, 
                        key=lambda x: (x.sector_relevance_scores.get(sector, 0) * 
                                     x.content_quality_score * x.impact_score), 
                        reverse=True)[:50]  # Top 50 most relevant
            
        except Exception as e:
            logger.error(f"Error fetching sector-specific events for {sector}: {e}")
            return []
    
    def _fetch_events_by_theme(self, theme: str, days_back: int) -> List[MacroEvent]:
        """Fetch events by specific theme with retry logic"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            start_str = start_date.strftime('%Y%m%d%H%M%S')
            end_str = end_date.strftime('%Y%m%d%H%M%S')
            
            # Build more sophisticated query
            query = f'"{theme}" AND (earnings OR revenue OR market OR business OR company OR stock)'
            
            params = {
                'query': query,
                'mode': 'artlist',
                'format': 'json',
                'maxrecords': 50,
                'startdatetime': start_str,
                'enddatetime': end_str,
                'sort': 'hybridrel'
            }
            
            response = None
            for attempt in range(self.max_retries):
                try:
                    response = self.session.get(f"{self.base_url}/doc/doc", params=params, timeout=45)
                    
                    if response.status_code == 429:
                        wait_time = 60 * (attempt + 1)
                        logger.warning(f"Rate limited, waiting {wait_time} seconds")
                        time.sleep(wait_time)
                        continue
                    elif response.status_code == 503:
                        wait_time = 30 * (attempt + 1)
                        logger.warning(f"Service unavailable, waiting {wait_time} seconds")
                        time.sleep(wait_time)
                        continue
                    
                    response.raise_for_status()
                    break
                    
                except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                    logger.warning(f"Connection issue on attempt {attempt + 1}: {e}")
                    if attempt < self.max_retries - 1:
                        time.sleep(10 * (attempt + 1))
                    continue
            
            if not response or response.status_code != 200:
                return []
            
            if not response.text.strip():
                return []
            
            try:
                data = response.json()
            except json.JSONDecodeError:
                return []
            
            events = []
            for article in data.get('articles', []):
                event = self._create_enhanced_event(article, theme)
                if event:
                    events.append(event)
            
            return events
            
        except Exception as e:
            logger.error(f"Error fetching events for theme {theme}: {e}")
            return []
    
    def _fetch_general_financial_events(self, days_back: int) -> List[MacroEvent]:
        """Fetch general financial/business events"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            start_str = start_date.strftime('%Y%m%d%H%M%S')
            end_str = end_date.strftime('%Y%m%d%H%M%S')
            
            # Focus on high-quality financial sources
            query = ('(earnings OR revenue OR "interest rate" OR merger OR acquisition OR "federal reserve") '
                    'AND sourcecountry:US')
            
            params = {
                'query': query,
                'mode': 'artlist',
                'format': 'json',
                'maxrecords': 100,
                'startdatetime': start_str,
                'enddatetime': end_str,
                'sort': 'hybridrel'
            }
            
            response = self.session.get(f"{self.base_url}/doc/doc", params=params, timeout=45)
            
            if response.status_code != 200 or not response.text.strip():
                return []
            
            data = response.json()
            events = []
            
            for article in data.get('articles', []):
                event = self._create_enhanced_event(article, 'general_financial')
                if event:
                    events.append(event)
            
            return events
            
        except Exception as e:
            logger.error(f"Error fetching general financial events: {e}")
            return []
    
    def _create_enhanced_event(self, article: Dict, source_theme: str) -> Optional[MacroEvent]:
        """Create an enhanced MacroEvent with improved data"""
        try:
            title = article.get('title', '')
            if not title or len(title) < 10:  # Filter very short titles
                return None
            
            # Enhanced tone calculation
            gdelt_tone = float(article.get('tone', 0))
            synthetic_tone = self._calculate_advanced_tone(title)
            final_tone = gdelt_tone if gdelt_tone != 0 else synthetic_tone
            
            # Create enhanced event
            event = MacroEvent(
                date=article.get('seendate', ''),
                title=title,
                source=article.get('domain', ''),
                tone=final_tone,
                goldstein_scale=0,
                num_mentions=1,
                event_type=self._classify_enhanced_event_type(title),
                countries=self._parse_countries(article.get('sourcecountry', '')),
                themes=self._parse_themes(article.get('themes', '')),
                impact_score=1.0,  # Will be recalculated later
                url=article.get('url', ''),
                language=article.get('language', ''),
                word_count=int(article.get('wordcount', 0))
            )
            
            # Set geographic impact
            event.geographic_impact = self._determine_geographic_impact(event)
            
            return event
            
        except Exception as e:
            logger.warning(f"Error creating event from article: {e}")
            return None
    
    def _calculate_advanced_tone(self, title: str) -> float:
        """Advanced tone calculation using contextual sentiment analysis"""
        title_lower = title.lower()
        
        # Enhanced sentiment dictionaries with weights
        sentiment_patterns = {
            # Very positive (3.0)
            'surge': 3.0, 'soar': 3.0, 'boom': 3.0, 'breakthrough': 3.0,
            'record high': 3.0, 'all-time high': 3.0, 'blockbuster': 3.0,
            
            # Positive (2.0)
            'gains': 2.0, 'rises': 2.0, 'up': 1.5, 'growth': 2.0, 'boost': 2.0,
            'rally': 2.0, 'bullish': 2.0, 'outperforms': 2.0, 'beats': 2.0,
            'strong': 1.5, 'positive': 1.5, 'optimistic': 1.5, 'recovery': 2.0,
            'success': 1.5, 'agreement': 1.5, 'deal': 1.0, 'partnership': 1.0,
            
            # Very negative (-3.0)
            'crash': -3.0, 'plunge': -3.0, 'collapse': -3.0, 'crisis': -3.0,
            'scandal': -3.0, 'fraud': -3.0, 'bankruptcy': -3.0,
            
            # Negative (-2.0)
            'falls': -2.0, 'drops': -2.0, 'decline': -2.0, 'bearish': -2.0,
            'underperforms': -2.0, 'misses': -2.0, 'weak': -1.5, 'negative': -1.5,
            'pessimistic': -1.5, 'warning': -2.0, 'concern': -1.5, 'risk': -1.0,
            'problem': -1.5, 'investigation': -2.0, 'lawsuit': -1.5,
            'conflict': -1.5, 'dispute': -1.0, 'shortage': -1.5, 'disruption': -2.0
        }
        
        total_sentiment = 0.0
        word_count = 0
        
        for word, weight in sentiment_patterns.items():
            if word in title_lower:
                total_sentiment += weight
                word_count += 1
        
        # Contextual modifiers
        if 'federal reserve' in title_lower or 'fed' in title_lower:
            # Fed news is typically more impactful
            total_sentiment *= 1.2
        
        if 'earnings' in title_lower:
            # Earnings news context matters more
            if any(word in title_lower for word in ['beats', 'tops', 'exceeds']):
                total_sentiment += 1.0
            elif any(word in title_lower for word in ['misses', 'disappoints', 'below']):
                total_sentiment -= 1.0
        
        # Normalize and bound the result
        if word_count > 0:
            avg_sentiment = total_sentiment / word_count
        else:
            avg_sentiment = 0.0
        
        return max(-5.0, min(5.0, avg_sentiment))
    
    def _classify_enhanced_event_type(self, title: str) -> str:
        """Enhanced event type classification with more granular categories"""
        title_lower = title.lower()
        
        # Hierarchical classification system
        event_types = {
            'Earnings & Financial Results': [
                'earnings', 'revenue', 'profit', 'loss', 'quarterly results',
                'financial results', 'guidance', 'outlook'
            ],
            'Monetary Policy': [
                'federal reserve', 'fed', 'interest rate', 'monetary policy',
                'inflation', 'central bank', 'fomc'
            ],
            'Corporate Actions': [
                'merger', 'acquisition', 'spinoff', 'ipo', 'bankruptcy',
                'restructuring', 'layoffs', 'hiring'
            ],
            'Regulatory & Legal': [
                'regulation', 'sec', 'fda', 'antitrust', 'lawsuit',
                'investigation', 'compliance', 'audit'
            ],
            'Trade & Geopolitical': [
                'trade war', 'tariff', 'sanctions', 'embargo', 'wto',
                'geopolitical', 'war', 'conflict'
            ],
            'Market Structure': [
                'volatility', 'liquidity', 'market structure', 'trading',
                'market maker', 'exchange'
            ],
            'Economic Indicators': [
                'gdp', 'unemployment', 'jobs report', 'consumer confidence',
                'retail sales', 'housing data', 'manufacturing'
            ],
            'Natural Disasters': [
                'earthquake', 'hurricane', 'flood', 'wildfire', 'tsunami',
                'natural disaster', 'weather'
            ],
            'Supply Chain': [
                'supply chain', 'shipping', 'port', 'cargo', 'logistics',
                'freight', 'transportation', 'disruption'
            ]
        }
        
        # Find best matching category
        for event_type, keywords in event_types.items():
            if any(keyword in title_lower for keyword in keywords):
                return event_type
        
        return 'Other Business News'
    
    def _calculate_enhanced_impact_score(self, event: MacroEvent, sector_relevance: float) -> float:
        """Calculate enhanced impact score considering multiple factors"""
        base_score = abs(event.tone) + 1.0
        
        # Sector relevance multiplier
        base_score *= (1.0 + sector_relevance * 0.5)
        
        # Content quality multiplier
        base_score *= (0.5 + event.content_quality_score * 0.5)
        
        # Event type multipliers
        type_multipliers = {
            'Earnings & Financial Results': 1.4,
            'Monetary Policy': 1.6,
            'Corporate Actions': 1.3,
            'Regulatory & Legal': 1.2,
            'Trade & Geopolitical': 1.5,
            'Economic Indicators': 1.3,
            'Natural Disasters': 1.1,
            'Supply Chain': 1.2
        }
        
        multiplier = type_multipliers.get(event.event_type, 1.0)
        base_score *= multiplier
        
        # Source quality bonus
        high_quality_sources = ['reuters', 'bloomberg', 'wsj', 'ft.com']
        if any(source in event.source.lower() for source in high_quality_sources):
            base_score *= 1.1
        
        # Recency bonus (more recent events have higher impact)
        if event.date:
            try:
                event_date = datetime.strptime(event.date[:8], '%Y%m%d')
                days_ago = (datetime.now() - event_date).days
                recency_factor = max(0.7, 1.0 - (days_ago * 0.05))
                base_score *= recency_factor
            except:
                pass  # If date parsing fails, use base score
        
        return base_score
    
    def _classify_event_urgency(self, event: MacroEvent) -> str:
        """Classify event urgency based on content and impact"""
        title_lower = event.title.lower()
        
        # Critical urgency indicators
        critical_indicators = [
            'breaking', 'urgent', 'emergency', 'crisis', 'crash',
            'suspend', 'halt', 'immediate', 'alert'
        ]
        
        if any(indicator in title_lower for indicator in critical_indicators):
            return 'critical'
        
        # High urgency indicators
        high_indicators = [
            'earnings', 'fed', 'federal reserve', 'merger', 'acquisition',
            'bankruptcy', 'investigation', 'lawsuit', 'rate cut', 'rate hike'
        ]
        
        if any(indicator in title_lower for indicator in high_indicators):
            return 'high'
        
        # Medium urgency (market-relevant news)
        if (event.content_quality_score > 0.6 and 
            any(sector_score > 2.0 for sector_score in event.sector_relevance_scores.values())):
            return 'medium'
        
        return 'low'
    
    def _remove_duplicate_events(self, events: List[MacroEvent]) -> List[MacroEvent]:
        """Remove duplicate events based on title similarity"""
        unique_events = []
        seen_titles = set()
        
        for event in events:
            # Create a normalized title for comparison
            normalized_title = re.sub(r'[^\w\s]', '', event.title.lower())
            normalized_title = ' '.join(normalized_title.split()[:8])  # First 8 words
            
            # Check for similarity with existing titles
            is_duplicate = False
            for seen_title in seen_titles:
                similarity = self._calculate_title_similarity(normalized_title, seen_title)
                if similarity > 0.8:  # 80% similarity threshold
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                seen_titles.add(normalized_title)
                unique_events.append(event)
        
        return unique_events
    
    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles using Jaccard similarity"""
        words1 = set(title1.split())
        words2 = set(title2.split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _parse_countries(self, country_str: str) -> List[str]:
        """Parse country string into list"""
        if not country_str:
            return []
        return [c.strip() for c in country_str.split(',') if c.strip()]
    
    def _parse_themes(self, theme_str: str) -> List[str]:
        """Parse theme string into list"""
        if not theme_str:
            return []
        return [t.strip() for t in theme_str.split(';') if t.strip()]
    
    def _determine_geographic_impact(self, event: MacroEvent) -> List[str]:
        """Determine geographic impact of event"""
        impact_regions = []
        title_lower = event.title.lower()
        
        # Global impact indicators
        global_indicators = [
            'global', 'worldwide', 'international', 'fed', 'federal reserve',
            'world bank', 'imf', 'g7', 'g20', 'opec'
        ]
        
        if any(indicator in title_lower for indicator in global_indicators):
            impact_regions.append('Global')
        
        # Regional impact
        if 'us' in event.countries or 'usa' in event.countries:
            impact_regions.append('North America')
        
        if any(country in event.countries for country in ['china', 'japan', 'korea']):
            impact_regions.append('Asia Pacific')
        
        if any(country in event.countries for country in ['germany', 'france', 'uk', 'italy']):
            impact_regions.append('Europe')
        
        return impact_regions or ['Regional']

class EnhancedMacroSentimentAnalyzer:
    """Enhanced macro sentiment analyzer with improved accuracy"""
    
    def __init__(self):
        self.gdelt = EnhancedGDELTAnalyzer()
        self.classifier = EnhancedSectorClassifier()
    
    def analyze_sector_sentiment(self, 
                               symbol: str, 
                               days_back: int = 7,
                               min_quality_threshold: float = 0.6) -> Dict:
        """
        Enhanced sector sentiment analysis with improved filtering and scoring
        """
        try:
            # Get sector for the symbol
            sector = self.classifier.get_sector(symbol)
            
            logger.info(f"Analyzing enhanced sentiment for {symbol} in {sector} sector")
            
            # Get sector-specific events using enhanced filtering
            relevant_events = self.gdelt.get_sector_specific_events(
                sector=sector,
                days_back=days_back,
                min_quality_score=min_quality_threshold
            )
            
            if not relevant_events:
                logger.info(f"No high-quality relevant events found for {symbol}")
                return self._create_neutral_result(symbol, sector, days_back)
            
            # Calculate comprehensive sentiment metrics
            sentiment_metrics = self._calculate_comprehensive_sentiment(relevant_events, sector)
            
            # Generate detailed impact assessment
            impact_analysis = self._generate_detailed_impact_analysis(relevant_events, sector)
            
            # Risk assessment
            risk_analysis = self._generate_risk_analysis(relevant_events, sector)
            
            # Trend analysis
            trend_analysis = self._analyze_sentiment_trends(relevant_events)
            
            # Create comprehensive result
            result = {
                'symbol': symbol,
                'sector': sector,
                'analysis_timestamp': datetime.now().isoformat(),
                'days_analyzed': days_back,
                'data_quality': {
                    'total_events_found': len(relevant_events),
                    'average_quality_score': np.mean([e.content_quality_score for e in relevant_events]),
                    'average_relevance_score': np.mean([e.sector_relevance_scores.get(sector, 0) for e in relevant_events]),
                    'source_diversity': len(set(e.source for e in relevant_events))
                },
                'sentiment_metrics': sentiment_metrics,
                'impact_analysis': impact_analysis,
                'risk_analysis': risk_analysis,
                'trend_analysis': trend_analysis,
                'top_events': self._get_top_events_summary(relevant_events, sector),
                'methodology_notes': self._get_methodology_notes()
            }
            
            # Save enhanced results
            self._save_enhanced_results(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in enhanced sentiment analysis for {symbol}: {e}")
            return {'error': str(e), 'symbol': symbol, 'sector': sector}
    
    def _calculate_comprehensive_sentiment(self, events: List[MacroEvent], sector: str) -> Dict:
        """Calculate comprehensive sentiment metrics"""
        if not events:
            return {'overall_score': 0.0, 'confidence': 'low', 'distribution': {}}
        
        # Weighted sentiment calculation
        weighted_scores = []
        for event in events:
            sector_relevance = event.sector_relevance_scores.get(sector, 0)
            quality_weight = event.content_quality_score
            relevance_weight = min(1.0, sector_relevance / 5.0)  # Normalize to 0-1
            
            combined_weight = quality_weight * relevance_weight * event.impact_score
            weighted_scores.append((event.tone, combined_weight))
        
        # Calculate weighted average
        total_weighted_sentiment = sum(score * weight for score, weight in weighted_scores)
        total_weight = sum(weight for _, weight in weighted_scores)
        
        overall_sentiment = total_weighted_sentiment / total_weight if total_weight > 0 else 0.0
        
        # Convert to -100 to 100 scale
        normalized_sentiment = max(-100, min(100, overall_sentiment * 20))
        
        # Calculate confidence based on data quality and quantity
        confidence = self._calculate_confidence_level(events, total_weight)
        
        # Sentiment distribution
        sentiment_distribution = self._calculate_sentiment_distribution(events)
        
        # Event urgency breakdown
        urgency_breakdown = self._calculate_urgency_breakdown(events)
        
        return {
            'overall_score': round(normalized_sentiment, 2),
            'confidence': confidence,
            'sentiment_distribution': sentiment_distribution,
            'urgency_breakdown': urgency_breakdown,
            'data_quality_metrics': {
                'weighted_events': len([w for _, w in weighted_scores if w > 0.1]),
                'total_weight': round(total_weight, 2),
                'average_event_quality': round(np.mean([e.content_quality_score for e in events]), 2)
            }
        }
    
    def _calculate_confidence_level(self, events: List[MacroEvent], total_weight: float) -> str:
        """Calculate confidence level based on data quality and quantity"""
        if len(events) < 3:
            return 'low'
        
        avg_quality = np.mean([e.content_quality_score for e in events])
        source_diversity = len(set(e.source for e in events))
        
        if (len(events) >= 10 and avg_quality >= 0.7 and 
            source_diversity >= 5 and total_weight >= 20):
            return 'very_high'
        elif (len(events) >= 7 and avg_quality >= 0.6 and 
              source_diversity >= 4 and total_weight >= 15):
            return 'high'
        elif (len(events) >= 5 and avg_quality >= 0.5 and 
              source_diversity >= 3 and total_weight >= 10):
            return 'medium'
        else:
            return 'low'
    
    def _calculate_sentiment_distribution(self, events: List[MacroEvent]) -> Dict:
        """Calculate distribution of sentiment across events"""
        positive = len([e for e in events if e.tone > 0.5])
        negative = len([e for e in events if e.tone < -0.5])
        neutral = len(events) - positive - negative
        
        total = len(events)
        return {
            'positive': round(positive / total * 100, 1) if total > 0 else 0,
            'negative': round(negative / total * 100, 1) if total > 0 else 0,
            'neutral': round(neutral / total * 100, 1) if total > 0 else 0
        }
    
    def _calculate_urgency_breakdown(self, events: List[MacroEvent]) -> Dict:
        """Calculate breakdown by event urgency"""
        urgency_counts = Counter(e.event_urgency for e in events)
        total = len(events)
        
        return {
            urgency: round(count / total * 100, 1) if total > 0 else 0
            for urgency, count in urgency_counts.items()
        }
    
    def _generate_detailed_impact_analysis(self, events: List[MacroEvent], sector: str) -> Dict:
        """Generate detailed impact analysis"""
        if not events:
            return {'summary': 'No significant events detected', 'factors': []}
        
        # Categorize events by type
        event_type_analysis = self._analyze_by_event_type(events)
        
        # Geographic impact analysis
        geographic_analysis = self._analyze_geographic_impact(events)
        
        # Timeline analysis
        timeline_analysis = self._analyze_event_timeline(events)
        
        # Key themes analysis
        theme_analysis = self._analyze_key_themes(events, sector)
        
        # Generate summary
        avg_sentiment = np.mean([e.tone for e in events])
        sentiment_label = self._get_sentiment_label(avg_sentiment)
        
        summary = (f"Sector sentiment is {sentiment_label} based on {len(events)} "
                  f"high-quality events. Key drivers include {theme_analysis['top_themes'][:2]}.")
        
        return {
            'summary': summary,
            'event_type_breakdown': event_type_analysis,
            'geographic_impact': geographic_analysis,
            'timeline_pattern': timeline_analysis,
            'key_themes': theme_analysis,
            'confidence_factors': self._identify_confidence_factors(events)
        }
    
    def _analyze_sentiment_trends(self, events: List[MacroEvent]) -> Dict:
        """Analyze sentiment trends and patterns"""
        if len(events) < 5:
            return {'trend': 'insufficient_data', 'pattern': 'unknown'}
        
        # Sort events by date
        dated_events = []
        for event in events:
            if event.date and len(event.date) >= 8:
                try:
                    event_date = datetime.strptime(event.date[:8], '%Y%m%d')
                    dated_events.append((event_date, event.tone, event.impact_score))
                except:
                    continue
        
        if len(dated_events) < 3:
            return {'trend': 'insufficient_data', 'pattern': 'unknown'}
        
        dated_events.sort(key=lambda x: x[0])  # Sort by date
        
        # Calculate trend using linear regression on sentiment
        dates_numeric = [(d[0] - dated_events[0][0]).days for d in dated_events]
        sentiments = [d[1] for d in dated_events]
        
        try:
            # Simple linear regression
            n = len(dates_numeric)
            sum_x = sum(dates_numeric)
            sum_y = sum(sentiments)
            sum_xy = sum(x * y for x, y in zip(dates_numeric, sentiments))
            sum_x2 = sum(x * x for x in dates_numeric)
            
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x) if (n * sum_x2 - sum_x * sum_x) != 0 else 0
            
            # Determine trend
            if abs(slope) < 0.01:
                trend = 'stable'
            elif slope > 0:
                trend = 'improving'
            else:
                trend = 'declining'
            
            # Volatility analysis
            volatility = np.std(sentiments) if len(sentiments) > 1 else 0
            volatility_level = 'high' if volatility > 1.5 else 'medium' if volatility > 0.8 else 'low'
            
            return {
                'trend': trend,
                'trend_strength': abs(slope),
                'volatility': volatility_level,
                'recent_sentiment': sentiments[-3:],  # Last 3 data points
                'pattern': self._identify_sentiment_pattern(sentiments)
            }
            
        except:
            return {'trend': 'unknown', 'pattern': 'unknown'}
    
    def _identify_sentiment_pattern(self, sentiments: List[float]) -> str:
        """Identify patterns in sentiment data"""
        if len(sentiments) < 4:
            return 'insufficient_data'
        
        # Look for specific patterns
        recent = sentiments[-4:]
        
        if all(s > 0 for s in recent):
            return 'consistently_positive'
        elif all(s < 0 for s in recent):
            return 'consistently_negative'
        elif recent[0] < 0 and recent[-1] > 0:
            return 'recovering'
        elif recent[0] > 0 and recent[-1] < 0:
            return 'deteriorating'
        else:
            return 'mixed'
    
    def _get_sentiment_label(self, sentiment_score: float) -> str:
        """Convert numeric sentiment to descriptive label"""
        if sentiment_score > 2:
            return 'very positive'
        elif sentiment_score > 0.5:
            return 'positive'
        elif sentiment_score > -0.5:
            return 'neutral'
        elif sentiment_score > -2:
            return 'negative'
        else:
            return 'very negative'
    
    def _identify_confidence_factors(self, events: List[MacroEvent]) -> List[str]:
        """Identify factors that affect confidence in the analysis"""
        factors = []
        
        if len(events) >= 10:
            factors.append('Large sample size increases confidence')
        elif len(events) < 5:
            factors.append('Small sample size reduces confidence')
        
        avg_quality = np.mean([e.content_quality_score for e in events])
        if avg_quality >= 0.8:
            factors.append('High average content quality')
        elif avg_quality < 0.5:
            factors.append('Lower content quality may affect accuracy')
        
        source_count = len(set(e.source for e in events))
        if source_count >= 5:
            factors.append('Good source diversity')
        elif source_count < 3:
            factors.append('Limited source diversity')
        
        urgency_distribution = Counter(e.event_urgency for e in events)
        if urgency_distribution.get('high', 0) + urgency_distribution.get('critical', 0) > len(events) * 0.3:
            factors.append('High proportion of urgent events increases reliability')
        
        return factors
    
    def _get_top_events_summary(self, events: List[MacroEvent], sector: str, limit: int = 10) -> List[Dict]:
        """Get summary of top events for the sector"""
        # Sort by combined relevance and impact
        sorted_events = sorted(
            events,
            key=lambda e: e.sector_relevance_scores.get(sector, 0) * e.impact_score * e.content_quality_score,
            reverse=True
        )
        
        top_events = []
        for event in sorted_events[:limit]:
            top_events.append({
                'title': event.title,
                'date': event.date[:8] if event.date else '',
                'source': event.source,
                'url': event.url,
                'sentiment': round(event.tone, 2),
                'sentiment_label': self._get_sentiment_label(event.tone),
                'event_type': event.event_type,
                'urgency': event.event_urgency,
                'impact_score': round(event.impact_score, 2),
                'sector_relevance': round(event.sector_relevance_scores.get(sector, 0), 2),
                'content_quality': round(event.content_quality_score, 2)
            })
        
        return top_events
    
    def _get_methodology_notes(self) -> Dict:
        """Provide notes on the analysis methodology"""
        return {
            'filtering_approach': 'Multi-layered filtering using content quality, source reliability, and sector relevance',
            'sentiment_calculation': 'Weighted average based on event impact, quality, and sector relevance',
            'confidence_factors': 'Based on sample size, source diversity, content quality, and event urgency',
            'limitations': [
                'Analysis limited to English-language sources',
                'Relies on GDELT event database availability',
                'Sentiment analysis may miss nuanced context',
                'Recent events may be weighted more heavily'
            ],
            'strengths': [
                'Advanced content filtering reduces noise',
                'Multi-dimensional relevance scoring',
                'Quality-weighted sentiment calculation',
                'Comprehensive risk and trend analysis'
            ]
        }
    
    def _create_neutral_result(self, symbol: str, sector: str, days_back: int) -> Dict:
        """Create neutral result when no relevant events are found"""
        return {
            'symbol': symbol,
            'sector': sector,
            'analysis_timestamp': datetime.now().isoformat(),
            'days_analyzed': days_back,
            'data_quality': {
                'total_events_found': 0,
                'note': 'No high-quality sector-relevant events found'
            },
            'sentiment_metrics': {
                'overall_score': 0.0,
                'confidence': 'low',
                'sentiment_distribution': {'neutral': 100.0},
                'note': 'Neutral sentiment due to lack of relevant events'
            },
            'impact_analysis': {
                'summary': f'No significant macro events detected for {sector} sector in the analyzed period',
                'confidence_factors': ['Limited data available for analysis']
            },
            'risk_analysis': {
                'overall_risk_level': 'minimal',
                'risk_score': 0.0,
                'note': 'No specific risk factors identified'
            },
            'trend_analysis': {
                'trend': 'insufficient_data',
                'pattern': 'unknown'
            },
            'methodology_notes': self._get_methodology_notes()
        }
    
    def _save_enhanced_results(self, result_data: Dict) -> None:
        """Save enhanced analysis results"""
        try:
            newsdata_dir = './newsdata'
            if not os.path.exists(newsdata_dir):
                os.makedirs(newsdata_dir)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            symbol = result_data.get('symbol', 'unknown')
            filename = f"enhanced_analysis_{symbol}_{timestamp}.json"
            filepath = os.path.join(newsdata_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved enhanced analysis results to {filepath}")
            
            # Also save a summary CSV for easy analysis
            self._save_summary_csv(result_data, newsdata_dir, timestamp)
            
        except Exception as e:
            logger.error(f"Error saving enhanced analysis results: {e}")
    
    def _save_summary_csv(self, result_data: Dict, newsdata_dir: str, timestamp: str) -> None:
        """Save a summary CSV of the analysis"""
        try:
            csv_filename = f"analysis_summary_{timestamp}.csv"
            csv_filepath = os.path.join(newsdata_dir, csv_filename)
            
            # Create summary data
            summary_data = [{
                'symbol': result_data.get('symbol', ''),
                'sector': result_data.get('sector', ''),
                'analysis_date': timestamp,
                'overall_sentiment_score': result_data.get('sentiment_metrics', {}).get('overall_score', 0),
                'confidence_level': result_data.get('sentiment_metrics', {}).get('confidence', 'unknown'),
                'total_events': result_data.get('data_quality', {}).get('total_events_found', 0),
                'avg_quality_score': result_data.get('data_quality', {}).get('average_quality_score', 0),
                'risk_level': result_data.get('risk_analysis', {}).get('overall_risk_level', 'unknown'),
                'trend': result_data.get('trend_analysis', {}).get('trend', 'unknown')
            }]
            
            df = pd.DataFrame(summary_data)
            df.to_csv(csv_filepath, index=False, encoding='utf-8')
            
            logger.info(f"Saved analysis summary CSV to {csv_filepath}")
            
        except Exception as e:
            logger.error(f"Error saving summary CSV: {e}")
    def _analyze_by_event_type(self, events: List[MacroEvent]) -> Dict:
        """Analyze events by type and their sentiment impact"""
        type_analysis = defaultdict(lambda: {'count': 0, 'avg_sentiment': 0.0, 'impact': 0.0})
        
        for event in events:
            event_type = event.event_type
            type_analysis[event_type]['count'] += 1
            type_analysis[event_type]['avg_sentiment'] += event.tone
            type_analysis[event_type]['impact'] += event.impact_score
        
        # Calculate averages
        for event_type, data in type_analysis.items():
            if data['count'] > 0:
                data['avg_sentiment'] /= data['count']
                data['avg_impact'] = data['impact'] / data['count']
        
        return dict(type_analysis)
    
    def _analyze_geographic_impact(self, events: List[MacroEvent]) -> Dict:
        """Analyze geographic distribution of impact"""
        geographic_impact = Counter()
        
        for event in events:
            for region in event.geographic_impact:
                geographic_impact[region] += event.impact_score
        
        return dict(geographic_impact)
    
    def _analyze_event_timeline(self, events: List[MacroEvent]) -> Dict:
        """Analyze sentiment trends over time"""
        try:
            # Group events by date
            daily_sentiment = defaultdict(list)
            
            for event in events:
                if event.date and len(event.date) >= 8:
                    date_str = event.date[:8]  # YYYYMMDD
                    daily_sentiment[date_str].append(event.tone)
            
            # Calculate daily averages
            daily_averages = {
                date: np.mean(sentiments) 
                for date, sentiments in daily_sentiment.items()
            }
            
            if len(daily_averages) >= 3:
                dates = sorted(daily_averages.keys())
                recent_sentiment = np.mean([daily_averages[d] for d in dates[-2:]])
                earlier_sentiment = np.mean([daily_averages[d] for d in dates[:-2]])
                
                trend = 'improving' if recent_sentiment > earlier_sentiment else 'declining'
                return {
                    'trend': trend,
                    'recent_avg': round(recent_sentiment, 2),
                    'earlier_avg': round(earlier_sentiment, 2),
                    'data_points': len(daily_averages)
                }
        except:
            pass
        
        return {'trend': 'insufficient_data', 'data_points': 0}
    
    def _analyze_key_themes(self, events: List[MacroEvent], sector: str) -> Dict:
        """Analyze key themes driving sentiment"""
        theme_counter = Counter()
        theme_sentiment = defaultdict(list)
        
        for event in events:
            # Extract themes from event
            themes = event.themes + [event.event_type]
            
            for theme in themes:
                if theme and len(theme) > 3:  # Filter very short themes
                    theme_counter[theme] += 1
                    theme_sentiment[theme].append(event.tone)
        
        # Get top themes with their sentiment
        top_themes = []
        for theme, count in theme_counter.most_common(5):
            avg_sentiment = np.mean(theme_sentiment[theme])
            top_themes.append({
                'theme': theme,
                'frequency': count,
                'avg_sentiment': round(avg_sentiment, 2),
                'sentiment_label': self._get_sentiment_label(avg_sentiment)
            })
        
        return {
            'top_themes': [t['theme'] for t in top_themes],
            'theme_details': top_themes
        }
    
    def _generate_risk_analysis(self, events: List[MacroEvent], sector: str) -> Dict:
        """Generate comprehensive risk analysis"""
        risk_factors = []
        risk_score = 0.0
        
        # Identify negative events with high impact
        negative_events = [e for e in events if e.tone < -1.0]
        high_impact_negative = [e for e in negative_events if e.impact_score > 2.0]
        
        for event in high_impact_negative[:5]:  # Top 5 risk factors
            risk_factors.append({
                'factor': event.title[:100] + "...",
                'severity': 'high' if event.impact_score > 3.0 else 'medium',
                'type': event.event_type,
                'urgency': event.event_urgency,
                'impact_score': round(event.impact_score, 2)
            })
            risk_score += abs(event.tone) * event.impact_score
        
        # Normalize risk score
        if risk_factors:
            risk_score = min(100, risk_score / len(risk_factors) * 10)
        
        # Risk level classification
        if risk_score > 50:
            risk_level = 'high'
        elif risk_score > 25:
            risk_level = 'medium'
        elif risk_score > 10:
            risk_level = 'low'
        else:
            risk_level = 'minimal'
        
        return {
            'overall_risk_level': risk_level,
            'risk_score': round(risk_score, 2),
            'key_risk_factors': risk_factors,
            'risk_distribution': {
                'regulatory': len([r for r in risk_factors if 'regulatory' in r['type'].lower()]),
                'market': len([r for r in risk_factors if 'market' in r['type'].lower() or 'earnings' in r['type'].lower()]),
                'operational': len([r for r in risk_factors if 'supply' in r['type'].lower()]),
                'geopolitical': len([r for r in risk_factors if 'geopolitical' in r['type'].lower()])
            }
        }
def main():
    """Enhanced example usage with comprehensive testing"""
    analyzer = EnhancedMacroSentimentAnalyzer()
    
    # Test with different symbols across sectors
    test_symbols = ["AAPL", "JPM", "JNJ", "XOM", "TSLA"]
    
    for symbol in test_symbols:
        print(f"\n{'='*80}")
        print(f"Enhanced Macro Sentiment Analysis for {symbol}")
        print(f"{'='*80}")
        
        result = analyzer.analyze_sector_sentiment(
            symbol=symbol, 
            days_back=14,  # 2 weeks of data
            min_quality_threshold=0.6
        )
        
        if 'error' not in result:
            # Print key results
            print(f"Sector: {result['sector']}")
            print(f"Overall Sentiment Score: {result['sentiment_metrics']['overall_score']}")
            print(f"Confidence Level: {result['sentiment_metrics']['confidence']}")
            print(f"Events Analyzed: {result['data_quality']['total_events_found']}")
            print(f"Average Quality Score: {result['data_quality']['average_quality_score']:.2f}")
            print(f"Risk Level: {result['risk_analysis']['overall_risk_level']}")
            print(f"Trend: {result['trend_analysis']['trend']}")
            
            # Print top events
            print(f"\nTop 3 Most Relevant Events:")
            for i, event in enumerate(result['top_events'][:3], 1):
                print(f"{i}. {event['title'][:80]}...")
                print(f"   Sentiment: {event['sentiment_label']} ({event['sentiment']})")
                print(f"   Source: {event['source']}")
                print(f"   Relevance: {event['sector_relevance']:.1f}/5.0")
                print()
            
        else:
            print(f"Error analyzing {symbol}: {result['error']}")
        
        # Add delay between analyses to be respectful to APIs
        if symbol != test_symbols[-1]:  # Don't sleep after last symbol
            time.sleep(5)

# Backward compatibility wrapper for existing server.py integration
class MacroSentimentAnalyzer:
    """Legacy compatibility wrapper for existing API endpoints"""
    
    def __init__(self):
        self.enhanced_analyzer = EnhancedMacroSentimentAnalyzer()
    
    def analyze_macro_sentiment(self, symbol: str, days_back: int = 7) -> Dict:
        """Legacy API method that returns simplified format for server.py"""
        try:
            # Use enhanced analyzer but return simplified format
            enhanced_result = self.enhanced_analyzer.analyze_sector_sentiment(
                symbol=symbol,
                days_back=days_back,
                min_quality_threshold=0.5
            )
            
            if 'error' in enhanced_result:
                return enhanced_result
            
            # Convert enhanced format to legacy format
            return {
                'symbol': enhanced_result['symbol'],
                'sector': enhanced_result['sector'],
                'analysis_date': enhanced_result['analysis_timestamp'],
                'days_analyzed': enhanced_result['days_analyzed'],
                'macro_sentiment_score': enhanced_result['sentiment_metrics']['overall_score'],
                'total_events': enhanced_result['data_quality']['total_events_found'],
                'relevant_events': enhanced_result['data_quality']['total_events_found'],
                'impact_assessment': enhanced_result['impact_analysis']['summary'],
                'top_events': [
                    {
                        'date': event['date'],
                        'title': event['title'],
                        'source': event['source'],
                        'url': event['url'],
                        'tone': event['sentiment'],
                        'event_type': event['event_type'],
                        'impact_score': event['impact_score'],
                        'countries': [],  # Simplified for legacy compatibility
                        'themes': []
                    }
                    for event in enhanced_result['top_events']
                ],
                'event_breakdown': self._create_event_breakdown(enhanced_result['top_events']),
                'risk_factors': [
                    factor['factor'] for factor in 
                    enhanced_result['risk_analysis'].get('key_risk_factors', [])
                ]
            }
            
        except Exception as e:
            logger.error(f"Error in legacy macro sentiment analysis: {e}")
            return {'error': str(e)}
    
    def get_sector_outlook(self, sector: str, days_back: int = 7) -> Dict:
        """Legacy sector outlook method"""
        try:
            # Find a representative symbol for the sector
            sector_symbols = {
                'Technology': 'AAPL',
                'Financial': 'JPM',
                'Healthcare': 'JNJ',
                'Energy': 'XOM',
                'Consumer Discretionary': 'HD',
                'Consumer Staples': 'PG',
                'Industrial': 'BA',
                'Materials': 'LIN',
                'Utilities': 'NEE',
                'Real Estate': 'AMT',
                'Communications': 'VZ'
            }
            
            representative_symbol = sector_symbols.get(sector, 'AAPL')
            result = self.analyze_macro_sentiment(representative_symbol, days_back)
            
            if 'error' not in result:
                return {
                    'sector': sector,
                    'analysis_date': result['analysis_date'],
                    'sector_sentiment_score': result['macro_sentiment_score'],
                    'total_relevant_events': result['total_events'],
                    'outlook': self._get_outlook_from_score(result['macro_sentiment_score']),
                    'key_events': result['top_events'][:5],
                    'event_types': result['event_breakdown']
                }
            else:
                return result
                
        except Exception as e:
            return {'error': str(e)}
    
    def _create_event_breakdown(self, events: List[Dict]) -> Dict[str, int]:
        """Create event breakdown for legacy compatibility"""
        breakdown = {}
        for event in events:
            event_type = event.get('event_type', 'Other')
            breakdown[event_type] = breakdown.get(event_type, 0) + 1
        return breakdown
    
    def _get_outlook_from_score(self, score: float) -> str:
        """Convert score to outlook text"""
        if score > 20:
            return "Very Positive"
        elif score > 5:
            return "Positive"
        elif score > -5:
            return "Neutral"
        elif score > -20:
            return "Negative"
        else:
            return "Very Negative"

analyze = MacroSentimentAnalyzer()
    
analyze.analyze_macro_sentiment("AMZN", 30)