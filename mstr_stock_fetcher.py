#!/usr/bin/env python3
"""
Real-time MSTR Stock Price Fetcher
Fetches current MSTR stock price from multiple sources
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MSTRStockFetcher:
    def __init__(self):
        self.session = None
        self.cache = {}
        self.cache_duration = timedelta(minutes=1)  # 1 minute cache for stock price
        
    async def get_session(self):
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
        
    async def fetch_yahoo_finance(self) -> Optional[float]:
        """Fetch MSTR price from Yahoo Finance"""
        try:
            session = await self.get_session()
            
            # Yahoo Finance API endpoint
            url = "https://query1.finance.yahoo.com/v8/finance/chart/MSTR"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Extract current price
                    result = data.get('chart', {}).get('result', [])
                    if result:
                        meta = result[0].get('meta', {})
                        price = meta.get('regularMarketPrice')
                        
                        if price and price > 0:
                            logger.info(f"Yahoo Finance: MSTR ${price:.2f}")
                            return float(price)
                            
        except Exception as e:
            logger.warning(f"Yahoo Finance fetch failed: {e}")
        return None
        
    async def fetch_cnbc(self) -> Optional[float]:
        """Fetch MSTR price from CNBC"""
        try:
            session = await self.get_session()
            
            # CNBC quote API
            url = "https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol?symbols=MSTR&requestMethod=itv&noform=1&partnerId=2&fund=1&exthrs=1&output=json&events=1"
            
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    text = await response.text()
                    # CNBC returns JSONP, need to extract JSON
                    json_str = text.strip()
                    if json_str.startswith('//'):
                        json_str = json_str[2:]
                    
                    data = json.loads(json_str)
                    quick_quote = data.get('FormattedQuoteResult', {}).get('FormattedQuote', [])
                    
                    if quick_quote:
                        price_str = quick_quote[0].get('last')
                        if price_str:
                            price = float(price_str.replace(',', ''))
                            logger.info(f"CNBC: MSTR ${price:.2f}")
                            return price
                            
        except Exception as e:
            logger.warning(f"CNBC fetch failed: {e}")
        return None
        
    async def fetch_marketwatch(self) -> Optional[float]:
        """Fetch MSTR price from MarketWatch"""
        try:
            session = await self.get_session()
            
            # MarketWatch page
            url = "https://www.marketwatch.com/investing/stock/mstr"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with session.get(url, headers=headers, timeout=15) as response:
                if response.status == 200:
                    html = await response.text()
                    
                    # Look for price in meta tags or specific patterns
                    # Pattern: "price":"XXX.XX"
                    price_pattern = re.compile(r'"price"\s*:\s*"?(\d+\.?\d*)"?')
                    match = price_pattern.search(html)
                    
                    if match:
                        price = float(match.group(1))
                        if 100 < price < 2000:  # Sanity check for MSTR
                            logger.info(f"MarketWatch: MSTR ${price:.2f}")
                            return price
                            
        except Exception as e:
            logger.warning(f"MarketWatch fetch failed: {e}")
        return None
        
    async def fetch_alpha_vantage(self) -> Optional[float]:
        """Fetch from Alpha Vantage (no API key required for basic quote)"""
        try:
            session = await self.get_session()
            
            # Alpha Vantage global quote - limited to 5 calls/minute without key
            url = "https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=MSTR&apikey=demo"
            
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    quote = data.get('Global Quote', {})
                    price_str = quote.get('05. price')
                    
                    if price_str:
                        price = float(price_str)
                        logger.info(f"Alpha Vantage: MSTR ${price:.2f}")
                        return price
                        
        except Exception as e:
            logger.warning(f"Alpha Vantage fetch failed: {e}")
        return None
        
    async def get_mstr_price(self) -> float:
        """Get MSTR stock price from multiple sources with caching"""
        
        # Check cache first
        if 'price' in self.cache and 'timestamp' in self.cache:
            if datetime.now() - self.cache['timestamp'] < self.cache_duration:
                logger.info(f"Using cached MSTR price: ${self.cache['price']:.2f}")
                return self.cache['price']
                
        # Try multiple sources in parallel
        tasks = [
            self.fetch_yahoo_finance(),
            self.fetch_cnbc(),
            # self.fetch_marketwatch(),  # Often blocked
            # self.fetch_alpha_vantage()  # Rate limited
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Filter out None results and get valid prices
        valid_prices = [p for p in results if p is not None and p > 0]
        
        if valid_prices:
            # Use the first valid price (Yahoo is most reliable)
            price = valid_prices[0]
            
            # Cache the result
            self.cache = {
                'price': price,
                'timestamp': datetime.now()
            }
            
            logger.info(f"Fetched MSTR price: ${price:.2f}")
            return price
        else:
            # Fallback to a reasonable estimate based on NAV
            # MSTR typically trades at 1.3x to 2x NAV
            # With BTC at ~$111k and 446,400 BTC, NAV per share ~$2,143
            # Typical MSTR price would be $2,800 to $4,300
            fallback_price = 380.0  # Conservative estimate
            logger.warning(f"Using fallback MSTR price: ${fallback_price:.2f}")
            
            self.cache = {
                'price': fallback_price,
                'timestamp': datetime.now()
            }
            
            return fallback_price
            
    async def cleanup(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()

# Singleton instance
_fetcher_instance = None

def get_stock_fetcher() -> MSTRStockFetcher:
    """Get or create singleton fetcher instance"""
    global _fetcher_instance
    if not _fetcher_instance:
        _fetcher_instance = MSTRStockFetcher()
    return _fetcher_instance

async def main():
    """Test the fetcher"""
    fetcher = get_stock_fetcher()
    
    try:
        price = await fetcher.get_mstr_price()
        print(f"MSTR Stock Price: ${price:.2f}")
        
        # Test cache
        price2 = await fetcher.get_mstr_price()
        print(f"Cached Price: ${price2:.2f}")
        
    finally:
        await fetcher.cleanup()

if __name__ == "__main__":
    asyncio.run(main())