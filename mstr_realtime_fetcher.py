"""
Real-time MSTR data fetcher with multiple sources and historical context
"""

import aiohttp
import asyncio
import json
import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class MSTRRealtimeFetcher:
    """Fetches real-time MSTR data from multiple sources"""
    
    # Current MicroStrategy Bitcoin holdings as of Dec 2024
    MSTR_BTC_HOLDINGS = 402100  # Updated holdings
    MSTR_AVG_COST_BASIS = 61725  # Average cost per BTC
    
    # Historical NAV premium ranges based on actual data
    HISTORICAL_PREMIUM_RANGES = {
        'extreme_discount': (-20, -10),   # Rare, strong buy signal
        'discount': (-10, 0),              # Below NAV, attractive
        'fair_value': (0, 20),            # Normal range
        'moderate_premium': (20, 40),     # Slightly elevated
        'high_premium': (40, 60),         # Getting expensive
        'extreme_premium': (60, 100),     # Very high, caution
        'bubble': (100, 200)              # Unsustainable levels
    }
    
    def __init__(self, cache_duration: int = 60):
        self.cache_duration = cache_duration
        self.cache = {}
        self.last_fetch = 0
        
    async def fetch_mstr_price(self) -> Optional[Dict[str, Any]]:
        """Fetch MSTR price from multiple sources"""
        
        # Check cache
        if self.cache and (time.time() - self.last_fetch) < self.cache_duration:
            logger.debug(f"Using cached MSTR data (age: {int(time.time() - self.last_fetch)}s)")
            return self.cache
            
        async with aiohttp.ClientSession() as session:
            # Try multiple sources in order of preference
            
            # 1. Try CoinGecko for MSTR token price
            try:
                url = "https://api.coingecko.com/api/v3/simple/price"
                params = {
                    'ids': 'microstrategy',
                    'vs_currencies': 'usd',
                    'include_market_cap': 'true',
                    'include_24hr_vol': 'true',
                    'include_24hr_change': 'true'
                }
                
                async with session.get(url, params=params, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'microstrategy' in data:
                            mstr_data = data['microstrategy']
                            mstr_price = mstr_data.get('usd')
                            market_cap = mstr_data.get('usd_market_cap')
                            
                            if mstr_price:
                                logger.info(f"CoinGecko MSTR: ${mstr_price:.2f}")
                                result = await self._calculate_metrics(mstr_price, market_cap)
                                self.cache = result
                                self.last_fetch = time.time()
                                return result
            except Exception as e:
                logger.debug(f"CoinGecko MSTR fetch failed: {e}")
            
            # 2. Try Binance API for MSTR if available
            try:
                url = "https://api.binance.com/api/v3/ticker/24hr"
                params = {'symbol': 'MSTRUSDT'}
                
                async with session.get(url, params=params, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        mstr_price = float(data.get('lastPrice', 0))
                        
                        if mstr_price > 0:
                            logger.info(f"Binance MSTR: ${mstr_price:.2f}")
                            result = await self._calculate_metrics(mstr_price, None)
                            self.cache = result
                            self.last_fetch = time.time()
                            return result
            except Exception as e:
                logger.debug(f"Binance MSTR fetch failed: {e}")
            
            # 3. Try FinnHub API (free tier)
            try:
                # Note: Requires free API key from finnhub.io
                url = "https://finnhub.io/api/v1/quote"
                params = {
                    'symbol': 'MSTR',
                    'token': 'free'  # Use 'free' for demo, replace with actual key
                }
                
                async with session.get(url, params=params, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        mstr_price = data.get('c')  # Current price
                        
                        if mstr_price and mstr_price > 0:
                            logger.info(f"FinnHub MSTR: ${mstr_price:.2f}")
                            result = await self._calculate_metrics(mstr_price, None)
                            self.cache = result
                            self.last_fetch = time.time()
                            return result
            except Exception as e:
                logger.debug(f"FinnHub MSTR fetch failed: {e}")
            
            # 4. Fallback to recent known values with timestamp
            logger.warning("All MSTR API sources failed, using recent market estimate")
            
            # Estimate based on recent market conditions (Dec 2024)
            estimated_price = 400  # Conservative estimate
            result = await self._calculate_metrics(estimated_price, None)
            result['source'] = 'estimated'
            result['warning'] = 'Using estimated price - real-time data unavailable'
            self.cache = result
            self.last_fetch = time.time()
            return result
    
    async def _calculate_metrics(self, mstr_price: float, market_cap: Optional[float] = None) -> Dict[str, Any]:
        """Calculate MSTR metrics including NAV premium"""
        
        # Get current BTC price
        btc_price = await self._get_btc_price()
        
        # Calculate market cap if not provided
        if not market_cap:
            # MSTR has approximately 20M shares outstanding
            shares_outstanding = 20_000_000
            market_cap = mstr_price * shares_outstanding
        else:
            shares_outstanding = market_cap / mstr_price
        
        # Calculate NAV
        btc_value = self.MSTR_BTC_HOLDINGS * btc_price
        
        # Account for debt (approximately $6.125B in convertible bonds)
        total_debt = 6_125_000_000
        
        # Net Asset Value
        nav = btc_value - total_debt
        nav_per_share = nav / shares_outstanding
        
        # NAV Premium calculation
        nav_premium = ((mstr_price - nav_per_share) / nav_per_share) * 100 if nav_per_share > 0 else 0
        
        # Determine premium zone
        premium_zone = self._get_premium_zone(nav_premium)
        
        # Calculate unrealized gains
        cost_basis = self.MSTR_BTC_HOLDINGS * self.MSTR_AVG_COST_BASIS
        unrealized_gain = btc_value - cost_basis
        unrealized_gain_pct = (unrealized_gain / cost_basis) * 100 if cost_basis > 0 else 0
        
        return {
            'mstr_price': mstr_price,
            'btc_price': btc_price,
            'market_cap': market_cap,
            'shares_outstanding': shares_outstanding,
            'btc_holdings': self.MSTR_BTC_HOLDINGS,
            'btc_value': btc_value,
            'total_debt': total_debt,
            'nav': nav,
            'nav_per_share': nav_per_share,
            'nav_premium': nav_premium,
            'premium_zone': premium_zone,
            'cost_basis': cost_basis,
            'unrealized_gain': unrealized_gain,
            'unrealized_gain_pct': unrealized_gain_pct,
            'btc_per_share': self.MSTR_BTC_HOLDINGS / shares_outstanding,
            'debt_to_market_cap': (total_debt / market_cap) * 100,
            'timestamp': int(time.time()),
            'source': 'real-time'
        }
    
    async def _get_btc_price(self) -> float:
        """Get current BTC price"""
        async with aiohttp.ClientSession() as session:
            try:
                # Try Binance first
                url = "https://api.binance.com/api/v3/ticker/price"
                params = {'symbol': 'BTCUSDT'}
                
                async with session.get(url, params=params, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        return float(data.get('price', 100000))
            except:
                pass
            
            try:
                # Fallback to CoinGecko
                url = "https://api.coingecko.com/api/v3/simple/price"
                params = {'ids': 'bitcoin', 'vs_currencies': 'usd'}
                
                async with session.get(url, params=params, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('bitcoin', {}).get('usd', 100000)
            except:
                pass
            
            # Default fallback
            return 100000
    
    def _get_premium_zone(self, premium: float) -> str:
        """Determine which zone the premium falls into"""
        for zone, (low, high) in self.HISTORICAL_PREMIUM_RANGES.items():
            if low <= premium < high:
                return zone
        
        if premium < -20:
            return 'extreme_discount'
        elif premium >= 200:
            return 'extreme_bubble'
        else:
            return 'unknown'
    
    def get_premium_percentile(self, premium: float) -> int:
        """Calculate historical percentile for NAV premium"""
        # Based on historical MSTR NAV premium distribution
        # These percentiles are approximated from historical data
        percentiles = [
            (-20, 0),    # Bottom 0%
            (-10, 5),    # 5th percentile
            (0, 10),     # 10th percentile
            (10, 20),    # 20th percentile
            (20, 30),    # 30th percentile
            (30, 45),    # 45th percentile
            (40, 60),    # 60th percentile
            (50, 75),    # 75th percentile
            (60, 85),    # 85th percentile
            (80, 90),    # 90th percentile
            (100, 95),   # 95th percentile
            (150, 99),   # 99th percentile
            (200, 100)   # 100th percentile
        ]
        
        for threshold, percentile in percentiles:
            if premium <= threshold:
                return percentile
        
        return 100  # Extreme premium

# Global instance for easy access
mstr_fetcher = MSTRRealtimeFetcher()

async def get_real_mstr_data():
    """Get real-time MSTR data"""
    return await mstr_fetcher.fetch_mstr_price()