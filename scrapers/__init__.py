#!/usr/bin/env python3
"""
Modular scrapers package for stock sentiment analysis

This package contains individual scrapers that can be used to gather news and sentiment data
from various financial news sources.
"""

from .base_scraper import BaseScraper, SentimentData
from .google_news_scraper import GoogleNewsScraper
from .newsapi_scraper import NewsAPIScraper
from .yahoo_finance_scraper import YahooFinanceScraper
from .marketwatch_scraper import MarketWatchScraper
from .seeking_alpha_scraper import SeekingAlphaScraper
from .seeking_alpha_scraper_pydoll import SeekingAlphaScraperPydoll
from .benzinga_scraper import BenzingaScraper
from .financial_times_scraper import FinancialTimesScraper
from .bloomberg_scraper import BloombergScraper
from .bloomberg_scraper_pydoll import BloombergScraperPydoll
from .reuters_scraper import ReutersScraper

__all__ = [
    'BaseScraper',
    'SentimentData',
    'GoogleNewsScraper',
    'NewsAPIScraper', 
    'YahooFinanceScraper',
    'MarketWatchScraper',
    'SeekingAlphaScraper',
    'SeekingAlphaScraperPydoll',
    'BenzingaScraper',
    'FinancialTimesScraper',
    'BloombergScraper',
    'BloombergScraperPydoll',
    'ReutersScraper'
]

# Available scrapers registry
AVAILABLE_SCRAPERS = {
    'google_news': GoogleNewsScraper,
    'newsapi': NewsAPIScraper,
    'yahoo_finance': YahooFinanceScraper,
    'marketwatch': MarketWatchScraper,
    'seeking_alpha': SeekingAlphaScraper,
    'seeking_alpha_pydoll': SeekingAlphaScraperPydoll,  # Enhanced anti-bot version
    'benzinga': BenzingaScraper,
    'financial_times': FinancialTimesScraper,
    'bloomberg': BloombergScraper,
    'bloomberg_pydoll': BloombergScraperPydoll,  # Enhanced anti-bot version
    'reuters': ReutersScraper
}