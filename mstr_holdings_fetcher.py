#!/usr/bin/env python3
"""
MicroStrategy Holdings Dynamic Fetcher
Fetches real-time MSTR holdings and metrics from multiple sources
Updates every 30 minutes and stores in SQLite
"""

import asyncio
import aiohttp
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MSTRHoldingsFetcher:
    def __init__(self, db_path='bitcoin_analyzer.db'):
        self.db_path = db_path
        self.session = None
        self.cache = {}
        self.cache_duration = timedelta(minutes=30)
        self.last_update = None
        
        # Initialize database
        self._init_database()
        
    def _init_database(self):
        """Initialize MSTR holdings table in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mstr_holdings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                btc_holdings REAL,
                avg_cost_basis REAL,
                shares_outstanding REAL,
                debt_total REAL,
                stock_price REAL,
                market_cap REAL,
                convertible_notes TEXT,
                source TEXT,
                raw_data TEXT
            )
        ''')
        
        # Create index for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_mstr_holdings_timestamp 
            ON mstr_holdings(timestamp DESC)
        ''')
        
        conn.commit()
        conn.close()
        logger.info("MSTR holdings table initialized")
        
    async def fetch_from_coingecko(self) -> Optional[Dict]:
        """Fetch MSTR data from CoinGecko API"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
                
            # CoinGecko has MSTR company treasury data
            url = "https://api.coingecko.com/api/v3/companies/public_treasury/microstrategy"
            
            async with self.session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Extract holdings data
                    holdings = {
                        'btc_holdings': data.get('total_holdings', 0),
                        'btc_value_usd': data.get('total_value_usd', 0),
                        'source': 'coingecko'
                    }
                    
                    logger.info(f"CoinGecko: {holdings['btc_holdings']} BTC")
                    return holdings
                    
        except Exception as e:
            logger.warning(f"CoinGecko fetch failed: {e}")
        return None
        
    async def fetch_from_saylortracker(self) -> Optional[Dict]:
        """Fetch MSTR data from SaylorTracker API"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
                
            url = "https://api.saylortracker.com/v1/treasury/microstrategy"
            
            async with self.session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    holdings = {
                        'btc_holdings': data.get('btc_balance', 0),
                        'avg_cost_basis': data.get('avg_purchase_price', 0),
                        'total_cost': data.get('total_investment', 0),
                        'source': 'saylortracker'
                    }
                    
                    logger.info(f"SaylorTracker: {holdings['btc_holdings']} BTC")
                    return holdings
                    
        except Exception as e:
            logger.warning(f"SaylorTracker fetch failed: {e}")
        return None
        
    async def fetch_from_bitcointreasuries(self) -> Optional[Dict]:
        """Fetch MSTR data from BitcoinTreasuries.net"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
                
            url = "https://bitcointreasuries.net/api"
            
            async with self.session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Find MicroStrategy in the data
                    for company in data.get('companies', []):
                        if 'microstrategy' in company.get('name', '').lower():
                            holdings = {
                                'btc_holdings': company.get('total_holdings', 0),
                                'btc_value_usd': company.get('total_value_usd', 0),
                                'percentage_of_supply': company.get('percentage_of_total_supply', 0),
                                'source': 'bitcointreasuries'
                            }
                            
                            logger.info(f"BitcoinTreasuries: {holdings['btc_holdings']} BTC")
                            return holdings
                            
        except Exception as e:
            logger.warning(f"BitcoinTreasuries fetch failed: {e}")
        return None
        
    async def scrape_strategy_site(self) -> Optional[Dict]:
        """Scrape MSTR holdings from strategy.com or similar sites"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
                
            # Try to scrape from known MSTR tracking sites
            urls = [
                "https://www.microstrategy.com/en/investor-relations",
                "https://saylortracker.com/",
                "https://bitcointreasuries.net/"
            ]
            
            for url in urls:
                try:
                    async with self.session.get(url, timeout=15) as response:
                        if response.status == 200:
                            html = await response.text()
                            
                            # Look for patterns like "446,400 BTC" or "446400 bitcoins"
                            btc_pattern = re.compile(r'(\d{3,6}[,.]?\d{0,3})\s*(?:BTC|bitcoin|Bitcoin)', re.IGNORECASE)
                            
                            matches = btc_pattern.findall(html)
                            if matches:
                                # Clean and convert the number
                                btc_str = matches[0].replace(',', '').replace('.', '')
                                btc_holdings = float(btc_str)
                                
                                if 300000 < btc_holdings < 600000:  # Sanity check
                                    holdings = {
                                        'btc_holdings': btc_holdings,
                                        'source': f'scraped_{url.split("/")[2]}'
                                    }
                                    logger.info(f"Scraped from {url}: {btc_holdings} BTC")
                                    return holdings
                                    
                except Exception as e:
                    logger.debug(f"Scraping {url} failed: {e}")
                    
        except Exception as e:
            logger.warning(f"Web scraping failed: {e}")
        return None
        
    async def fetch_stock_price(self) -> Optional[float]:
        """Fetch current MSTR stock price"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
                
            # Try Yahoo Finance API
            url = "https://query1.finance.yahoo.com/v8/finance/chart/MSTR"
            
            async with self.session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    price = data['chart']['result'][0]['meta']['regularMarketPrice']
                    logger.info(f"MSTR stock price: ${price}")
                    return price
                    
        except Exception as e:
            logger.warning(f"Stock price fetch failed: {e}")
            
        # Fallback to Alpha Vantage or other sources
        return None
        
    async def aggregate_data(self) -> Dict:
        """Aggregate data from multiple sources"""
        
        # Fetch from all sources in parallel
        tasks = [
            self.fetch_from_coingecko(),
            self.fetch_from_saylortracker(),
            self.fetch_from_bitcointreasuries(),
            self.scrape_strategy_site(),
            self.fetch_stock_price()
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Aggregate the data
        aggregated = {
            'btc_holdings': None,
            'avg_cost_basis': None,
            'shares_outstanding': 205.8e6,  # Default ~205.8M shares (Class A as of Dec 2024)
            'debt_total': 7.8e9,  # Default $7.8B debt
            'stock_price': None,
            'source': 'aggregated',
            'timestamp': datetime.now().isoformat()
        }
        
        # Get BTC holdings - prioritize most recent/reliable sources
        holdings_values = []
        for result in results[:-1]:  # Exclude stock price
            if result and 'btc_holdings' in result and result['btc_holdings'] > 0:
                holdings_values.append(result['btc_holdings'])
                
        if holdings_values:
            # Use the most common value or average if they're close
            if len(set(holdings_values)) == 1:
                aggregated['btc_holdings'] = holdings_values[0]
            else:
                # If values are within 5% of each other, average them
                min_val, max_val = min(holdings_values), max(holdings_values)
                if (max_val - min_val) / min_val < 0.05:
                    aggregated['btc_holdings'] = sum(holdings_values) / len(holdings_values)
                else:
                    # Use the most recent/reliable source
                    aggregated['btc_holdings'] = holdings_values[0]
                    
        # Get avg cost basis if available
        for result in results:
            if result and 'avg_cost_basis' in result and result['avg_cost_basis'] > 0:
                aggregated['avg_cost_basis'] = result['avg_cost_basis']
                break
                
        # Get stock price
        if results[-1]:
            aggregated['stock_price'] = results[-1]
            
        # Calculate market cap if we have stock price
        if aggregated['stock_price']:
            aggregated['market_cap'] = aggregated['stock_price'] * aggregated['shares_outstanding']
            
        # Use latest known values as fallback
        if not aggregated['btc_holdings']:
            aggregated['btc_holdings'] = 446400  # Dec 31, 2024 value
            logger.warning("Using fallback BTC holdings: 446,400")
            
        if not aggregated['avg_cost_basis']:
            aggregated['avg_cost_basis'] = 62428  # $27.9B / 446,400
            
        logger.info(f"Aggregated data: {aggregated['btc_holdings']} BTC @ ${aggregated['avg_cost_basis']}")
        
        return aggregated
        
    def save_to_database(self, data: Dict):
        """Save holdings data to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO mstr_holdings (
                btc_holdings, avg_cost_basis, shares_outstanding,
                debt_total, stock_price, market_cap, source, raw_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('btc_holdings'),
            data.get('avg_cost_basis'),
            data.get('shares_outstanding'),
            data.get('debt_total'),
            data.get('stock_price'),
            data.get('market_cap'),
            data.get('source'),
            json.dumps(data)
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Saved MSTR holdings to database: {data['btc_holdings']} BTC")
        
    def get_latest_holdings(self) -> Dict:
        """Get latest holdings from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT btc_holdings, avg_cost_basis, shares_outstanding,
                   debt_total, stock_price, market_cap, source, timestamp
            FROM mstr_holdings
            ORDER BY timestamp DESC
            LIMIT 1
        ''')
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'btc_holdings': row[0],
                'avg_cost_basis': row[1],
                'shares_outstanding': row[2],
                'debt_total': row[3],
                'stock_price': row[4],
                'market_cap': row[5],
                'source': row[6],
                'timestamp': row[7]
            }
        
        # Return default values if no data
        return {
            'btc_holdings': 446400,
            'avg_cost_basis': 62428,
            'shares_outstanding': 205.8e6,
            'debt_total': 7.8e9,
            'stock_price': None,
            'market_cap': None,
            'source': 'default',
            'timestamp': datetime.now().isoformat()
        }
        
    async def update_holdings(self):
        """Fetch and update holdings"""
        try:
            # Check if we need to update (30 minute cache)
            if self.last_update and \
               datetime.now() - self.last_update < self.cache_duration:
                logger.info("Using cached MSTR data")
                return self.cache
                
            logger.info("Fetching fresh MSTR holdings data...")
            
            # Aggregate data from all sources
            data = await self.aggregate_data()
            
            # Save to database
            self.save_to_database(data)
            
            # Update cache
            self.cache = data
            self.last_update = datetime.now()
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to update holdings: {e}")
            # Return latest from database as fallback
            return self.get_latest_holdings()
            
    async def start_periodic_updates(self):
        """Start periodic updates every 30 minutes"""
        while True:
            try:
                await self.update_holdings()
                await asyncio.sleep(1800)  # 30 minutes
            except Exception as e:
                logger.error(f"Periodic update failed: {e}")
                await asyncio.sleep(60)  # Retry in 1 minute
                
    async def cleanup(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()

# Singleton instance
_fetcher_instance = None

def get_fetcher() -> MSTRHoldingsFetcher:
    """Get or create singleton fetcher instance"""
    global _fetcher_instance
    if not _fetcher_instance:
        _fetcher_instance = MSTRHoldingsFetcher()
    return _fetcher_instance

async def main():
    """Test the fetcher"""
    fetcher = get_fetcher()
    
    try:
        # Test fetching
        data = await fetcher.update_holdings()
        print(f"Latest MSTR holdings: {json.dumps(data, indent=2)}")
        
        # Test database retrieval
        db_data = fetcher.get_latest_holdings()
        print(f"From database: {json.dumps(db_data, indent=2)}")
        
    finally:
        await fetcher.cleanup()

if __name__ == "__main__":
    asyncio.run(main())