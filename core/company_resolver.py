#!/usr/bin/env python3
"""
Company Name Resolver using Google Gemini API
DEPRECATED: Use core.gemini_client.GeminiClient directly for new code
Maintained for backward compatibility
"""

from typing import Optional, Dict
from .gemini_client import GeminiClient

class CompanyResolver:
    """
    DEPRECATED: Legacy company resolver interface
    Use core.gemini_client.GeminiClient directly for new implementations
    """
    
    def __init__(self, api_key: str = None):
        """Initialize the company resolver with Gemini API key"""
        try:
            self.client = GeminiClient(api_key)
            self.cache = {}  # In-memory cache for current session
        except Exception as e:
            raise e
    
    def resolve_company_name(self, symbol: str) -> Optional[str]:
        """
        DEPRECATED: Use GeminiClient.resolve_company_info() instead
        Resolve stock symbol to common company name
        """
        symbol = symbol.upper().strip()
        
        # Check in-memory cache first
        if symbol in self.cache:
            return self.cache[symbol]
        
        try:
            info = self.client.resolve_company_info(symbol)
            common_name = info.get('common_name')
            
            if common_name:
                self.cache[symbol] = common_name
                
            return common_name
        except Exception as e:
            print(f"[WARNING] Error resolving company name for {symbol}: {e}")
            return None
    
    def resolve_multiple_companies(self, symbols: list) -> Dict[str, Optional[str]]:
        """
        DEPRECATED: Resolve multiple stock symbols to company names
        """
        results = {}
        
        for symbol in symbols:
            results[symbol] = self.resolve_company_name(symbol)
            # Small delay handled by GeminiClient rate limiting
        
        return results


def create_example_api_config():
    """Create an example api_config.py file if it doesn't exist"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "api_config_example.py")
    
    if not os.path.exists(config_path):
        with open(config_path, 'w') as f:
            f.write("""#!/usr/bin/env python3
\"\"\"
API Configuration Example
Copy this file to api_config.py and add your API keys
\"\"\"

# Google Gemini API Key
# Get your free API key at: https://makersuite.google.com/app/apikey
GEMINI_API_KEY = 'your_gemini_api_key_here'
""")
        print(f"[INFO] Created example config file: {config_path}")


if __name__ == "__main__":
    """Test the company resolver"""
    try:
        resolver = CompanyResolver()
        
        # Test some common symbols
        test_symbols = ['NVDA', 'AAPL', 'TSLA', 'GOOGL', 'MSFT']
        
        print("Testing company name resolution:")
        for symbol in test_symbols:
            name = resolver.resolve_company_name(symbol)
            print(f"{symbol} -> {name}")
            
    except Exception as e:
        print(f"Test failed: {e}")
        create_example_api_config()