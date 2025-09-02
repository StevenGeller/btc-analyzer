import asyncio
import aiohttp
import numpy as np
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from database import Database

logger = logging.getLogger(__name__)

class MSTRBTCAnalyzer:
    """
    MSTR is the ultimate BTC proxy with unique dynamics:
    - 2-3x BTC leverage through options gamma
    - NAV premium/discount signals market sentiment
    - Saylor buying patterns are tradeable
    """
    
    def __init__(self, database: Database):
        self.db = database
        self.mstr_btc_holdings = 632457  # MicroStrategy BTC holdings from strategy.com
        self.init_database()
    
    def init_database(self):
        """Add MSTR-specific tables"""
        with self.db.get_connection() as conn:
            # MSTR price and NAV data
            conn.execute("""
                CREATE TABLE IF NOT EXISTS mstr_data (
                    timestamp INTEGER PRIMARY KEY,
                    price REAL NOT NULL,
                    volume REAL,
                    market_cap REAL,
                    nav_premium REAL,
                    beta_to_btc REAL,
                    options_volume REAL,
                    options_oi REAL
                )
            """)
            
            conn.execute("""CREATE INDEX IF NOT EXISTS idx_mstr_timestamp ON mstr_data(timestamp)""")
    
    async def fetch_mstr_data(self) -> Dict:
        """Fetch MSTR data from Yahoo Finance with fallback"""
        try:
            # Check if we have recent cached data (within 5 minutes)
            with self.db.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM mstr_data 
                    WHERE timestamp > ?
                    ORDER BY timestamp DESC LIMIT 1
                """, (int(time.time() - 300),))  # 5 minutes cache
                cached = cursor.fetchone()
                
                if cached:
                    # Convert Row to dict and return cached data
                    try:
                        cached_dict = dict(cached)
                        return {
                            'timestamp': cached_dict.get('timestamp', int(time.time())),
                            'price': cached_dict.get('price', 1800),
                            'volume': cached_dict.get('volume', 500000000),
                            'market_cap': cached_dict.get('market_cap', 38000000000),
                            'nav_premium': cached_dict.get('nav_premium', 40)
                        }
                    except:
                        pass  # Fall through to fetch
            
            async with aiohttp.ClientSession() as session:
                # Get MSTR stock data
                url = "https://query1.finance.yahoo.com/v8/finance/chart/MSTR"
                params = {
                    'interval': '5m',
                    'range': '1d',
                    'includePrePost': 'true'
                }
                
                # Add timeout to prevent hanging
                timeout = aiohttp.ClientTimeout(total=5)
                async with session.get(url, params=params, timeout=timeout) as response:
                    if response.status == 429:  # Rate limited
                        logger.warning("MSTR API rate limited, using fallback data")
                        return self._get_fallback_mstr_data()
                    
                    if response.status != 200:
                        raise Exception(f"MSTR API error: {response.status}")
                    
                    data = await response.json()
                    chart = data['chart']['result'][0]
                    meta = chart['meta']
                    
                    # Get current BTC price for NAV calculation
                    btc_price = await self._get_current_btc_price(session)
                    
                    # Calculate NAV premium
                    nav_value = self.mstr_btc_holdings * btc_price
                    shares_outstanding = 284.6e6  # 284.6M shares from strategy.com
                    nav_per_share = nav_value / shares_outstanding
                    
                    current_price = meta['regularMarketPrice']
                    nav_premium = ((current_price - nav_per_share) / nav_per_share) * 100
                    
                    return {
                        'price': current_price,
                        'volume': meta.get('regularMarketVolume', 0),
                        'market_cap': meta.get('marketCap', 0),
                        'nav_premium': nav_premium,
                        'timestamp': int(time.time())
                    }
                    
        except Exception as e:
            logger.error(f"MSTR data fetch error: {e}")
            return self._get_fallback_mstr_data()
    
    def _get_fallback_mstr_data(self) -> Dict:
        """Get fallback MSTR data from database or estimates"""
        try:
            with self.db.get_connection() as conn:
                # Get most recent MSTR data from database
                cursor = conn.execute("""
                    SELECT * FROM mstr_data 
                    ORDER BY timestamp DESC LIMIT 1
                """)
                result = cursor.fetchone()
                
                if result:
                    # Return last known data with updated timestamp
                    return {
                        'timestamp': int(time.time()),
                        'price': result['price'],
                        'volume': result['volume'] * 0.8,  # Reduce volume for stale data
                        'market_cap': result['market_cap'],
                        'nav_premium': result['nav_premium']
                    }
                else:
                    # Return estimated data based on typical values
                    return {
                        'timestamp': int(time.time()),
                        'price': 500,  # Typical MSTR price
                        'volume': 1_000_000,
                        'market_cap': 10_000_000_000,
                        'nav_premium': 150  # Typical premium
                    }
        except:
            return None
    
    async def _get_current_btc_price(self, session) -> float:
        """Get current BTC price for NAV calculation"""
        try:
            # Use CoinGecko for BTC price
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {'ids': 'bitcoin', 'vs_currencies': 'usd'}
            
            async with session.get(url, params=params) as response:
                data = await response.json()
                return data['bitcoin']['usd']
        except:
            # Fallback to database
            with self.db.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT price FROM price_data 
                    ORDER BY timestamp DESC LIMIT 1
                """)
                result = cursor.fetchone()
                return result['price'] if result else 100000  # Fallback
    
    def store_mstr_data(self, data: Dict):
        """Store MSTR data in database"""
        if not data:
            return
            
        with self.db.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO mstr_data 
                (timestamp, price, volume, market_cap, nav_premium)
                VALUES (?, ?, ?, ?, ?)
            """, (
                data['timestamp'],
                data['price'],
                data['volume'],
                data['market_cap'],
                data['nav_premium']
            ))
    
    async def analyze_mstr_btc_relationship(self) -> Dict:
        """
        Core MSTR analysis - the signals that actually matter
        """
        try:
            with self.db.get_connection() as conn:
                # Get recent MSTR and BTC data
                cursor = conn.execute("""
                    SELECT 
                        m.timestamp,
                        m.price as mstr_price,
                        m.volume as mstr_volume,
                        m.nav_premium,
                        b.price as btc_price
                    FROM mstr_data m
                    JOIN price_data b ON ABS(m.timestamp - b.timestamp) < 300
                    WHERE m.timestamp > ?
                    ORDER BY m.timestamp DESC
                    LIMIT 100
                """, (int(time.time() - 86400 * 2),))  # 2 days
                
                data = cursor.fetchall()
            
            if len(data) < 20:
                return {'signal': 'insufficient_data', 'message': 'Need more MSTR data'}
            
            # Extract price arrays
            mstr_prices = np.array([d['mstr_price'] for d in data])
            btc_prices = np.array([d['btc_price'] for d in data])
            nav_premiums = np.array([d['nav_premium'] for d in data if d['nav_premium']])
            
            # 1. Calculate MSTR Beta (leverage factor) - CURRENT not historical
            # First try to calculate from actual price movements
            beta_calculated = False
            
            if len(mstr_prices) > 1 and len(btc_prices) > 1:
                # Calculate percentage changes
                mstr_change_24h = ((mstr_prices[0] - mstr_prices[-1]) / mstr_prices[-1]) * 100 if len(mstr_prices) > 0 else 0
                btc_change_24h = ((btc_prices[0] - btc_prices[-1]) / btc_prices[-1]) * 100 if len(btc_prices) > 0 else 0
                
                # Current beta = MSTR % change / BTC % change
                if abs(btc_change_24h) > 0.1:  # BTC moved at least 0.1%
                    beta = mstr_change_24h / btc_change_24h
                    beta_calculated = True
                    
                    # Sanity check - cap at reasonable limits
                    if beta < 0:  # Inverse movement
                        beta = abs(beta)  # Use absolute value
                    if beta < 1.0:
                        beta = 1.0  # MSTR should at least match BTC
                    elif beta > 5.0:
                        beta = 5.0  # Cap at 5x
                    
                    correlation = 0.9 if beta_calculated else 0.85
                else:
                    # If BTC hasn't moved, calculate from returns
                    mstr_returns = np.diff(mstr_prices) / mstr_prices[:-1]
                    btc_returns = np.diff(btc_prices) / btc_prices[:-1]
                    
                    # Filter out zero returns
                    valid_indices = (np.abs(mstr_returns) > 1e-6) | (np.abs(btc_returns) > 1e-6)
                    mstr_returns = mstr_returns[valid_indices]
                    btc_returns = btc_returns[valid_indices]
                    
                    if len(mstr_returns) > 0 and np.std(btc_returns) > 1e-6:
                        beta = np.cov(mstr_returns, btc_returns)[0, 1] / np.var(btc_returns)
                        correlation = np.corrcoef(mstr_returns, btc_returns)[0, 1]
                        beta_calculated = True
                        
                        # Sanity limits
                        beta = max(1.0, min(5.0, abs(beta)))
                    else:
                        # Fallback to typical MSTR beta
                        beta = 2.5
                        correlation = 0.85
            else:
                # No data - use typical MSTR beta
                beta = 2.5
                correlation = 0.85
            
            # 2. NAV Premium Analysis (CRITICAL signal)
            current_premium = nav_premiums[0] if len(nav_premiums) > 0 else 0
            avg_premium = np.mean(nav_premiums) if len(nav_premiums) > 5 else current_premium
            
            # 3. Alpha Calculation (MSTR excess return vs expected beta return)
            if len(data) >= 24:
                mstr_24h_change = (mstr_prices[0] - mstr_prices[23]) / mstr_prices[23]
                btc_24h_change = (btc_prices[0] - btc_prices[23]) / btc_prices[23]
                
                # Expected return based on beta
                expected_mstr_return = btc_24h_change * beta
                
                # Alpha = Actual return - Expected return
                alpha = (mstr_24h_change - expected_mstr_return) * 100  # Convert to percentage
                
                # Divergence for backward compatibility
                divergence = mstr_24h_change - expected_mstr_return
            else:
                alpha = 0
                divergence = 0
            
            # 4. Generate Actionable Signals
            signals = []
            composite_signal = 0
            
            # NAV Premium Signals
            if current_premium > avg_premium + 20:  # Excessive premium
                signals.append({
                    'type': 'warning',
                    'message': f'⚠️ MSTR OVERVALUED - Trading {current_premium:.1f}% above Bitcoin value!',
                    'action': 'Consider buying BTC directly instead of MSTR',
                    'confidence': min(0.9, (current_premium - avg_premium) / 50)
                })
                composite_signal -= 0.3
                
            elif current_premium < avg_premium - 10:  # Discount opportunity
                signals.append({
                    'type': 'opportunity', 
                    'message': f'💰 MSTR DISCOUNT - Trading {abs(current_premium):.1f}% below fair value!',
                    'action': 'MSTR offers leveraged BTC exposure at discount',
                    'confidence': min(0.9, abs(current_premium - avg_premium) / 20)
                })
                composite_signal += 0.4
            
            # Divergence Signals (Leading indicator)
            if divergence > 0.03:  # MSTR leading to upside
                signals.append({
                    'type': 'leading',
                    'message': f'🚀 MSTR LEADING UP - Outperforming by {divergence*100:.1f}% (vs {beta:.1f}x expected)',
                    'action': 'MSTR front-running BTC pump - expect Bitcoin to follow',
                    'confidence': min(0.9, divergence * 20)
                })
                composite_signal += 0.3
                
            elif divergence < -0.03:  # MSTR lagging
                signals.append({
                    'type': 'lagging',
                    'message': f'📉 MSTR LAGGING - Underperforming by {abs(divergence)*100:.1f}%',
                    'action': 'Either MSTR catch-up trade or BTC reversal warning',
                    'confidence': min(0.8, abs(divergence) * 15)
                })
                composite_signal -= 0.2
            
            # Saylor Buying Zone (he buys dips religiously)
            btc_recent_avg = np.mean(btc_prices[:20])
            if btc_prices[0] < btc_recent_avg * 0.95:  # 5% below recent average
                signals.append({
                    'type': 'saylor_zone',
                    'message': f'🤖 SAYLOR BUY ZONE - BTC {((btc_prices[0]/btc_recent_avg-1)*100):+.1f}% from recent average',
                    'action': 'Watch for MSTR debt issuance or buyback announcements',
                    'confidence': 0.7
                })
                composite_signal += 0.2
            
            # High Beta Warning
            if beta > 3.5:
                signals.append({
                    'type': 'volatility',
                    'message': f'⚡ EXTREME LEVERAGE - MSTR showing {beta:.1f}x BTC volatility',
                    'action': 'Reduce position size - volatility is extreme',
                    'confidence': 0.8
                })
                composite_signal *= 0.7  # Reduce confidence in extreme volatility
            
            # Default message if no clear signals
            if not signals:
                signals.append({
                    'type': 'neutral',
                    'message': f'➡️ MSTR TRACKING BTC - {beta:.1f}x leverage, {current_premium:+.1f}% premium',
                    'action': 'Monitor for NAV discount or divergence opportunities',
                    'confidence': 0.5
                })
            
            # Get current MSTR price
            current_mstr_price = mstr_prices[0] if len(mstr_prices) > 0 else 500
            
            return {
                'price': float(current_mstr_price),
                'beta': float(beta) if np.isfinite(beta) else 2.5,
                'correlation': float(correlation) if np.isfinite(correlation) else 0.85,
                'nav_premium': float(current_premium) if np.isfinite(current_premium) else 0.0,
                'avg_premium': float(avg_premium) if np.isfinite(avg_premium) else 0.0,
                'alpha': float(alpha) if np.isfinite(alpha) else 0.0,
                'divergence': float(divergence) if np.isfinite(divergence) else 0.0,
                'composite_signal': float(np.clip(composite_signal, -1, 1)) if np.isfinite(composite_signal) else 0.0,
                'signals': signals,
                'last_updated': int(time.time()),
                'data_points': len(data)
            }
            
        except Exception as e:
            logger.error(f"MSTR analysis error: {e}")
            return {
                'error': str(e),
                'signals': [{
                    'type': 'error',
                    'message': '❌ MSTR analysis temporarily unavailable',
                    'action': 'Check data connection',
                    'confidence': 0
                }]
            }


class ETHBTCAnalyzer:
    """
    ETH/BTC ratio - the ultimate alt season detector
    """
    
    def __init__(self, database: Database):
        self.db = database
        self.init_database()
    
    def init_database(self):
        """Add ETH tracking tables"""
        with self.db.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS eth_data (
                    timestamp INTEGER PRIMARY KEY,
                    price REAL NOT NULL,
                    volume_24h REAL,
                    gas_price REAL,
                    market_cap REAL,
                    eth_btc_ratio REAL
                )
            """)
            
            conn.execute("""CREATE INDEX IF NOT EXISTS idx_eth_timestamp ON eth_data(timestamp)""")
    
    async def fetch_eth_data(self) -> Dict:
        """Fetch ETH data with caching and fallback"""
        try:
            # Check cache first (5 minute cache)
            with self.db.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM eth_data
                    WHERE timestamp > ?
                    ORDER BY timestamp DESC LIMIT 1
                """, (int(time.time() - 300),))
                cached = cursor.fetchone()
                
                if cached:
                    try:
                        cached_dict = dict(cached)
                        return {
                            'price': cached_dict.get('price', 4470),
                            'volume_24h': cached_dict.get('volume', 10000000000),
                            'market_cap': cached_dict.get('market_cap', 450000000000),
                            'eth_btc_ratio': cached_dict.get('eth_btc_ratio', 0.041),
                            'timestamp': cached_dict.get('timestamp', int(time.time()))
                        }
                    except:
                        pass  # Fall through to fetch
            
            # Try Binance API first (no rate limit)
            async with aiohttp.ClientSession() as session:
                try:
                    # Get ETH price from Binance
                    binance_url = "https://api.binance.com/api/v3/ticker/24hr"
                    params = {'symbol': 'ETHUSDT'}
                    
                    timeout = aiohttp.ClientTimeout(total=3)
                    async with session.get(binance_url, params=params, timeout=timeout) as response:
                        if response.status == 200:
                            data = await response.json()
                            eth_price = float(data['lastPrice'])
                            volume_24h = float(data['volume']) * eth_price
                            
                            # Get BTC price for ratio
                            btc_params = {'symbol': 'BTCUSDT'}
                            async with session.get(binance_url, params=btc_params) as btc_response:
                                if btc_response.status == 200:
                                    btc_data = await btc_response.json()
                                    btc_price = float(btc_data['lastPrice'])
                                    eth_btc_ratio = eth_price / btc_price
                                    
                                    return {
                                        'price': eth_price,
                                        'volume_24h': volume_24h,
                                        'market_cap': eth_price * 120_000_000,  # Approximate supply
                                        'eth_btc_ratio': eth_btc_ratio,
                                        'timestamp': int(time.time())
                                    }
                except:
                    pass  # Fall through to CoinGecko
                
                # Fallback to CoinGecko with rate limit handling
                url = "https://api.coingecko.com/api/v3/simple/price"
                params = {
                    'ids': 'ethereum,bitcoin',
                    'vs_currencies': 'usd',
                    'include_24hr_vol': 'true',
                    'include_market_cap': 'true'
                }
                
                timeout = aiohttp.ClientTimeout(total=5)
                async with session.get(url, params=params, timeout=timeout) as response:
                    if response.status == 429:  # Rate limited
                        logger.warning("ETH API rate limited, using fallback")
                        return self._get_fallback_eth_data()
                    
                    if response.status != 200:
                        raise Exception(f"ETH API error: {response.status}")
                    
                    data = await response.json()
                    eth_price = data['ethereum']['usd']
                    btc_price = data['bitcoin']['usd']
                    
                    return {
                        'price': eth_price,
                        'volume_24h': data['ethereum'].get('usd_24h_vol', 10_000_000_000),
                        'market_cap': data['ethereum'].get('usd_market_cap', eth_price * 120_000_000),
                        'eth_btc_ratio': eth_price / btc_price,
                        'timestamp': int(time.time())
                    }
                    
        except Exception as e:
            logger.error(f"ETH data fetch error: {e}")
            return self._get_fallback_eth_data()
    
    def _get_fallback_eth_data(self) -> Dict:
        """Get fallback ETH data from database"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM eth_data
                    ORDER BY timestamp DESC LIMIT 1
                """)
                result = cursor.fetchone()
                
                if result:
                    return {
                        'price': result['price'],
                        'volume_24h': result['volume'] * 0.8,
                        'market_cap': result['market_cap'],
                        'eth_btc_ratio': result['eth_btc_ratio'],
                        'timestamp': int(time.time())
                    }
                else:
                    # Default fallback values
                    return {
                        'price': 3800,  # Typical ETH price
                        'volume_24h': 10_000_000_000,
                        'market_cap': 450_000_000_000,
                        'eth_btc_ratio': 0.035,  # Typical ratio
                        'timestamp': int(time.time())
                    }
        except:
            return None
    
    async def _get_btc_price(self, session) -> float:
        """Get BTC price for ratio calculation"""
        try:
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {'ids': 'bitcoin', 'vs_currencies': 'usd'}
            
            async with session.get(url, params=params) as response:
                data = await response.json()
                return data['bitcoin']['usd']
        except:
            return 100000  # Fallback
    
    def store_eth_data(self, data: Dict):
        """Store ETH data"""
        if not data:
            return
            
        with self.db.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO eth_data 
                (timestamp, price, volume_24h, market_cap, eth_btc_ratio)
                VALUES (?, ?, ?, ?, ?)
            """, (
                data['timestamp'],
                data['price'],
                data['volume_24h'],
                data['market_cap'],
                data['eth_btc_ratio']
            ))
    
    async def analyze_eth_btc_ratio(self) -> Dict:
        """
        ETH/BTC ratio analysis - alt season detector
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT eth_btc_ratio, timestamp, price
                    FROM eth_data
                    WHERE timestamp > ?
                    ORDER BY timestamp DESC
                    LIMIT 100
                """, (int(time.time() - 86400 * 5),))  # 5 days
                
                data = cursor.fetchall()
            
            if len(data) < 10:
                return {'signal': 'insufficient_data'}
            
            # Convert Row objects to dicts for easier access
            data_dicts = [dict(d) for d in data]
            ratios = [d['eth_btc_ratio'] for d in data_dicts]
            eth_prices = [d['price'] for d in data_dicts]
            current_ratio = ratios[0]
            
            # Key levels (historical analysis)
            support_level = 0.050  # Strong historical support
            resistance_level = 0.080  # Historical resistance
            ma_20 = np.mean(ratios[:20]) if len(ratios) >= 20 else current_ratio
            
            signals = []
            composite_signal = 0
            
            # Support/Resistance Analysis
            if current_ratio <= support_level * 1.05:  # Near support
                signals.append({
                    'type': 'support',
                    'message': f'🎯 ETH/BTC AT SUPPORT - Ratio: {current_ratio:.4f} near {support_level:.3f}',
                    'action': 'Prime alt season setup - consider ETH/alt exposure',
                    'confidence': 0.8
                })
                composite_signal += 0.4
                
            elif current_ratio >= resistance_level * 0.95:  # Near resistance
                signals.append({
                    'type': 'resistance',
                    'message': f'⚠️ ETH/BTC EXTENDED - Ratio: {current_ratio:.4f} near {resistance_level:.3f}',
                    'action': 'Alt season peak - rotate back to BTC',
                    'confidence': 0.8
                })
                composite_signal -= 0.4
            
            # Trend Analysis
            if current_ratio > ma_20 * 1.02:  # Above MA
                trend_signal = 'alt_season'
                signals.append({
                    'type': 'trend',
                    'message': f'📈 ALT SEASON ACTIVE - ETH/BTC trending up: {current_ratio:.4f} vs {ma_20:.4f} avg',
                    'action': 'Maintain alt exposure while trend holds',
                    'confidence': 0.7
                })
                composite_signal += 0.2
                
            elif current_ratio < ma_20 * 0.98:  # Below MA
                trend_signal = 'btc_dominance'
                signals.append({
                    'type': 'trend',
                    'message': f'📉 BTC DOMINANCE - ETH/BTC trending down: {current_ratio:.4f} vs {ma_20:.4f} avg',
                    'action': 'Reduce alt exposure, increase BTC allocation',
                    'confidence': 0.7
                })
                composite_signal -= 0.2
            else:
                trend_signal = 'neutral'
            
            # Momentum Check
            if len(ratios) >= 7:
                weekly_change = (current_ratio - ratios[6]) / ratios[6] * 100
                if abs(weekly_change) > 5:
                    direction = "UP" if weekly_change > 0 else "DOWN"
                    signals.append({
                        'type': 'momentum',
                        'message': f'⚡ STRONG MOMENTUM - ETH/BTC {direction} {abs(weekly_change):.1f}% this week',
                        'action': f'Momentum trade: {"increase ETH" if weekly_change > 0 else "reduce ETH"} exposure',
                        'confidence': min(0.8, abs(weekly_change) / 10)
                    })
            
            # Default neutral message
            if not signals:
                signals.append({
                    'type': 'neutral',
                    'message': f'➡️ ETH/BTC NEUTRAL - Ratio: {current_ratio:.4f} (Range: {support_level:.3f}-{resistance_level:.3f})',
                    'action': 'Wait for clear breakout above/below range',
                    'confidence': 0.5
                })
            
            # Calculate ETH price from data or estimate from ratio
            if len(eth_prices) > 0:
                eth_price = eth_prices[0]
            else:
                # Estimate from ratio and typical BTC price
                eth_price = current_ratio * 109000  # Use current BTC price estimate
            
            return {
                'price': float(eth_price),
                'current_ratio': float(current_ratio) if np.isfinite(current_ratio) else 0.035,
                'ma_20': float(ma_20) if np.isfinite(ma_20) else 0.035,
                'support_level': support_level,
                'resistance_level': resistance_level,
                'trend_signal': trend_signal,
                'composite_signal': float(np.clip(composite_signal, -1, 1)) if np.isfinite(composite_signal) else 0.0,
                'signals': signals,
                'last_updated': int(time.time())
            }
            
        except Exception as e:
            logger.error(f"ETH/BTC analysis error: {e}")
            return {
                'error': str(e),
                'signals': [{
                    'type': 'error',
                    'message': '❌ ETH/BTC analysis temporarily unavailable',
                    'action': 'Check data connection',
                    'confidence': 0
                }]
            }


class SolanaAnalyzer:
    """Analyzes Solana momentum and alt season indicators"""
    
    def __init__(self, database: Database):
        self.db = database
        self._setup_sol_table()
    
    def _setup_sol_table(self):
        """Create Solana data table if it doesn't exist"""
        with self.db.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sol_data (
                    timestamp INTEGER PRIMARY KEY,
                    price REAL,
                    volume REAL,
                    market_cap REAL,
                    sol_btc_ratio REAL,
                    price_change_24h REAL
                )
            """)
            conn.execute("""CREATE INDEX IF NOT EXISTS idx_sol_timestamp ON sol_data(timestamp)""")
    
    async def fetch_sol_data(self) -> Dict:
        """Fetch Solana data from Binance"""
        try:
            # Check cache first (5 minute cache)
            with self.db.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM sol_data
                    WHERE timestamp > ?
                    ORDER BY timestamp DESC LIMIT 1
                """, (int(time.time() - 300),))
                cached = cursor.fetchone()
                
                if cached:
                    return {
                        'price': cached['price'],
                        'volume': cached['volume'],
                        'market_cap': cached['market_cap'],
                        'sol_btc_ratio': cached['sol_btc_ratio'],
                        'price_change_24h': cached['price_change_24h'],
                        'timestamp': cached['timestamp']
                    }
            
            async with aiohttp.ClientSession() as session:
                # Get SOL and BTC prices from Binance
                binance_url = "https://api.binance.com/api/v3/ticker/24hr"
                
                timeout = aiohttp.ClientTimeout(total=3)
                
                # Get SOL data
                sol_params = {'symbol': 'SOLUSDT'}
                async with session.get(binance_url, params=sol_params, timeout=timeout) as response:
                    if response.status == 200:
                        sol_data = await response.json()
                        sol_price = float(sol_data['lastPrice'])
                        sol_volume = float(sol_data['volume']) * sol_price
                        sol_change_24h = float(sol_data['priceChangePercent'])
                        
                        # Get BTC price for ratio
                        btc_params = {'symbol': 'BTCUSDT'}
                        async with session.get(binance_url, params=btc_params) as btc_response:
                            if btc_response.status == 200:
                                btc_data = await btc_response.json()
                                btc_price = float(btc_data['lastPrice'])
                                sol_btc_ratio = sol_price / btc_price
                                
                                return {
                                    'price': sol_price,
                                    'volume': sol_volume,
                                    'market_cap': sol_price * 450_000_000,  # Approximate circulating supply
                                    'sol_btc_ratio': sol_btc_ratio,
                                    'price_change_24h': sol_change_24h,
                                    'timestamp': int(time.time())
                                }
                
                return self._get_fallback_sol_data()
                
        except Exception as e:
            logger.error(f"SOL data fetch error: {e}")
            return self._get_fallback_sol_data()
    
    def _get_fallback_sol_data(self) -> Dict:
        """Get fallback SOL data"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM sol_data
                    ORDER BY timestamp DESC LIMIT 1
                """)
                result = cursor.fetchone()
                
                if result:
                    return {
                        'price': result['price'],
                        'volume': result['volume'] * 0.8,
                        'market_cap': result['market_cap'],
                        'sol_btc_ratio': result['sol_btc_ratio'],
                        'price_change_24h': 0,  # Unknown change
                        'timestamp': int(time.time())
                    }
                else:
                    # Default fallback values
                    return {
                        'price': 200,  # Typical SOL price
                        'volume': 2_000_000_000,
                        'market_cap': 90_000_000_000,
                        'sol_btc_ratio': 0.002,  # Typical ratio
                        'price_change_24h': 0,
                        'timestamp': int(time.time())
                    }
        except:
            return None
    
    def store_sol_data(self, data: Dict):
        """Store SOL data in database"""
        if not data:
            return
            
        with self.db.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO sol_data 
                (timestamp, price, volume, market_cap, sol_btc_ratio, price_change_24h)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                data['timestamp'],
                data['price'],
                data['volume'],
                data['market_cap'],
                data['sol_btc_ratio'],
                data.get('price_change_24h', 0)
            ))
    
    async def analyze_sol_momentum(self) -> Dict:
        """Analyze Solana momentum and market position"""
        try:
            with self.db.get_connection() as conn:
                # Get recent SOL data
                cursor = conn.execute("""
                    SELECT * FROM sol_data
                    WHERE timestamp > ?
                    ORDER BY timestamp DESC
                    LIMIT 100
                """, (int(time.time() - 86400 * 7),))  # 7 days
                
                data = cursor.fetchall()
            
            if len(data) < 10:
                return {'signal': 'insufficient_data', 'message': 'Need more SOL data'}
            
            # Current metrics
            current = data[0]
            current_price = current['price']
            current_ratio = current['sol_btc_ratio']
            change_24h = current['price_change_24h']
            
            # Calculate moving averages
            prices = [d['price'] for d in data[:20]] if len(data) >= 20 else [d['price'] for d in data]
            ratios = [d['sol_btc_ratio'] for d in data[:20]] if len(data) >= 20 else [d['sol_btc_ratio'] for d in data]
            
            ma_price = np.mean(prices)
            ma_ratio = np.mean(ratios)
            
            # Momentum signals
            price_momentum = (current_price - ma_price) / ma_price * 100
            ratio_momentum = (current_ratio - ma_ratio) / ma_ratio * 100
            
            signals = []
            composite_signal = 0
            
            # Strong pump signal
            if change_24h > 5 and ratio_momentum > 10:
                signals.append({
                    'type': 'bullish',
                    'message': f'🚀 SOL OUTPERFORMING - Up {change_24h:.1f}% today, ratio improving {ratio_momentum:.1f}%',
                    'action': 'Alt season momentum building - increase SOL exposure',
                    'confidence': 0.9
                })
                composite_signal = 0.8
            
            # Momentum building
            elif change_24h > 2 or ratio_momentum > 5:
                signals.append({
                    'type': 'momentum',
                    'message': f'📈 SOL MOMENTUM - Price ${current_price:.2f} ({change_24h:+.1f}%)',
                    'action': 'Consider adding to SOL positions',
                    'confidence': 0.7
                })
                composite_signal = 0.5
            
            # Weakness
            elif change_24h < -3 or ratio_momentum < -10:
                signals.append({
                    'type': 'bearish',
                    'message': f'📉 SOL WEAKNESS - Down {abs(change_24h):.1f}%, losing vs BTC',
                    'action': 'Reduce SOL exposure, rotate to BTC',
                    'confidence': 0.8
                })
                composite_signal = -0.6
            
            # Neutral
            else:
                signals.append({
                    'type': 'neutral',
                    'message': f'➡️ SOL STABLE - Price ${current_price:.2f}, ratio {current_ratio:.4f}',
                    'action': 'Hold current positions',
                    'confidence': 0.5
                })
                composite_signal = 0
            
            return {
                'price': current_price,
                'price_change_24h': change_24h,
                'sol_btc_ratio': current_ratio,
                'price_momentum': price_momentum,
                'ratio_momentum': ratio_momentum,
                'composite_signal': composite_signal,
                'signals': signals,
                'last_updated': current['timestamp']
            }
            
        except Exception as e:
            logger.error(f"SOL analysis error: {e}")
            return {
                'error': str(e),
                'signals': [{
                    'type': 'error',
                    'message': '❌ SOL analysis unavailable',
                    'action': 'Check data connection',
                    'confidence': 0
                }]
            }


class MultiAssetCorrelationManager:
    """
    Orchestrates all multi-asset analysis
    """
    
    def __init__(self, database: Database):
        self.db = database
        self.mstr_analyzer = MSTRBTCAnalyzer(database)
        self.eth_analyzer = ETHBTCAnalyzer(database)
        self.sol_analyzer = SolanaAnalyzer(database)
        self.last_update = 0
        self.current_analysis = {}
    
    async def update_all_data(self):
        """Fetch and store all multi-asset data"""
        try:
            # Fetch all data in parallel
            tasks = [
                self.mstr_analyzer.fetch_mstr_data(),
                self.eth_analyzer.fetch_eth_data(),
                self.sol_analyzer.fetch_sol_data()
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Store results
            if not isinstance(results[0], Exception):
                self.mstr_analyzer.store_mstr_data(results[0])
            
            if not isinstance(results[1], Exception):
                self.eth_analyzer.store_eth_data(results[1])
            
            if len(results) > 2 and not isinstance(results[2], Exception):
                self.sol_analyzer.store_sol_data(results[2])
                
            logger.info("Multi-asset data updated successfully")
            
        except Exception as e:
            logger.error(f"Multi-asset data update error: {e}")
    
    async def get_comprehensive_analysis(self) -> Dict:
        """Get complete multi-asset analysis"""
        try:
            current_time = time.time()
            
            # Don't update too frequently (every 2 minutes)
            if current_time - self.last_update < 120:
                return self.current_analysis if self.current_analysis else self._get_fallback_analysis()
            
            # Run all analyses in parallel
            tasks = [
                self.mstr_analyzer.analyze_mstr_btc_relationship(),
                self.eth_analyzer.analyze_eth_btc_ratio(),
                self.sol_analyzer.analyze_sol_momentum()
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            mstr_analysis = results[0] if not isinstance(results[0], Exception) else {'error': str(results[0])}
            eth_analysis = results[1] if not isinstance(results[1], Exception) else {'error': str(results[1])}
            sol_analysis = results[2] if len(results) > 2 and not isinstance(results[2], Exception) else {'error': 'No SOL data'}
            
            # Combine analyses
            self.current_analysis = {
                'mstr': mstr_analysis,
                'eth_btc': eth_analysis,
                'solana': sol_analysis,
                'market_phase': self._determine_market_phase(mstr_analysis, eth_analysis, sol_analysis),
                'composite_signal': self._calculate_composite_signal(mstr_analysis, eth_analysis, sol_analysis),
                'last_updated': int(current_time),
                'timestamp': int(current_time)
            }
            
            self.last_update = current_time
            return self.current_analysis
            
        except Exception as e:
            logger.error(f"Comprehensive analysis error: {e}")
            return self._get_fallback_analysis()
    
    def _determine_market_phase(self, mstr_analysis: Dict, eth_analysis: Dict, sol_analysis: Dict = None) -> Dict:
        """Determine overall market rotation phase with detailed condition tracking"""
        try:
            # Extract signals
            mstr_signal = mstr_analysis.get('composite_signal', 0)
            mstr_premium = mstr_analysis.get('nav_premium', 0)
            eth_signal = eth_analysis.get('composite_signal', 0)
            eth_trend = eth_analysis.get('trend_signal', 'neutral')
            
            sol_signal = 0
            sol_momentum = 0
            if sol_analysis and 'error' not in sol_analysis:
                sol_signal = sol_analysis.get('composite_signal', 0)
                sol_momentum = sol_analysis.get('price_momentum', 0)
            
            # Track all conditions
            conditions_checked = []
            
            # 1. Full Alt Season Check
            full_alt_check = sol_signal > 0.5 and eth_signal > 0.3
            conditions_checked.append({
                'name': 'Full Alt Season',
                'condition': f'SOL > 0.5 AND ETH > 0.3',
                'actual': f'SOL={sol_signal:.2f}, ETH={eth_signal:.2f}',
                'met': '✅' if full_alt_check else '❌'
            })
            
            # 2. Peak Euphoria Check
            peak_euphoria_check = mstr_premium > 30 and eth_trend == 'alt_season'
            conditions_checked.append({
                'name': 'Peak Euphoria',
                'condition': f'MSTR premium > 30 AND ETH trend = alt_season',
                'actual': f'Premium={mstr_premium:.1f}%, Trend={eth_trend}',
                'met': '✅' if peak_euphoria_check else '❌'
            })
            
            # 3. Risk On Check
            risk_on_check = mstr_signal > 0.3 and eth_signal > 0.2
            conditions_checked.append({
                'name': 'Risk On',
                'condition': f'MSTR > 0.3 AND ETH > 0.2',
                'actual': f'MSTR={mstr_signal:.2f}, ETH={eth_signal:.2f}',
                'met': '✅' if risk_on_check else '❌'
            })
            
            # 4. Flight to Quality Check
            flight_check = mstr_signal < -0.3 and eth_trend == 'btc_dominance'
            conditions_checked.append({
                'name': 'Flight to Quality',
                'condition': f'MSTR < -0.3 AND ETH trend = btc_dominance',
                'actual': f'MSTR={mstr_signal:.2f}, Trend={eth_trend}',
                'met': '✅' if flight_check else '❌'
            })
            
            # 5. Alt Season Check
            alt_season_check = eth_trend == 'alt_season' and mstr_signal > -0.2
            conditions_checked.append({
                'name': 'Alt Season',
                'condition': f'ETH trend = alt_season AND MSTR > -0.2',
                'actual': f'Trend={eth_trend}, MSTR={mstr_signal:.2f}',
                'met': '✅' if alt_season_check else '❌'
            })
            
            # Determine phase
            if full_alt_check:
                phase = {
                    'phase': 'full_altseason',
                    'message': '🚀 FULL ALT SEASON - SOL & ETH outperforming BTC',
                    'confidence': 0.9
                }
            elif peak_euphoria_check:
                phase = {
                    'phase': 'peak_euphoria',
                    'message': '🚨 PEAK EUPHORIA - MSTR premium high, alts pumping',
                    'confidence': 0.8
                }
            elif risk_on_check:
                phase = {
                    'phase': 'risk_on',
                    'message': '🚀 RISK ON - Both MSTR and ETH showing strength',
                    'confidence': 0.7
                }
            elif flight_check:
                phase = {
                    'phase': 'flight_to_quality',
                    'message': '🛡️ FLIGHT TO QUALITY - Capital rotating to BTC',
                    'confidence': 0.8
                }
            elif alt_season_check:
                phase = {
                    'phase': 'alt_season',
                    'message': '🌟 ALT SEASON - ETH leading, healthy rotation',
                    'confidence': 0.6
                }
            else:
                phase = {
                    'phase': 'neutral',
                    'message': 'No clear rotation pattern',
                    'confidence': 0.3
                }
            
            # Add detailed breakdown
            phase['market_conditions'] = {
                'mstr_signal': {'value': mstr_signal, 'label': 'neutral' if abs(mstr_signal) < 0.2 else 'bullish' if mstr_signal > 0 else 'bearish'},
                'mstr_premium': {'value': mstr_premium, 'label': 'extreme' if mstr_premium > 50 else 'high' if mstr_premium > 30 else 'normal'},
                'eth_signal': {'value': eth_signal, 'label': 'bullish' if eth_signal > 0.3 else 'neutral' if eth_signal > -0.3 else 'bearish'},
                'eth_trend': eth_trend,
                'sol_signal': {'value': sol_signal, 'label': 'bullish' if sol_signal > 0.3 else 'neutral' if sol_signal > -0.3 else 'bearish'},
                'sol_momentum': {'value': sol_momentum, 'label': 'positive' if sol_momentum > 0 else 'negative'}
            }
            phase['conditions_checked'] = conditions_checked
            
            return phase
            
        except Exception as e:
            logger.error(f"Market phase error: {e}")
            return {'phase': 'error', 'message': 'Phase detection error', 'confidence': 0}
    
    def _calculate_composite_signal(self, mstr_analysis: Dict, eth_analysis: Dict, sol_analysis: Dict = None) -> float:
        """Calculate overall multi-asset signal"""
        try:
            # Check for errors in analyses
            if 'error' in mstr_analysis or 'error' in eth_analysis:
                return 0.0
            
            mstr_signal = mstr_analysis.get('composite_signal', 0)
            eth_signal = eth_analysis.get('composite_signal', 0)
            sol_signal = 0
            
            if sol_analysis and 'error' not in sol_analysis:
                sol_signal = sol_analysis.get('composite_signal', 0)
            
            # Handle NaN or invalid values
            if not np.isfinite(mstr_signal):
                mstr_signal = 0.0
            if not np.isfinite(eth_signal):
                eth_signal = 0.0
            if not np.isfinite(sol_signal):
                sol_signal = 0.0
            
            # Weighted signals: MSTR 40%, ETH 30%, SOL 30%
            if sol_signal != 0:
                weighted_signal = mstr_signal * 0.4 + eth_signal * 0.3 + sol_signal * 0.3
            else:
                # Fallback if no SOL data
                weighted_signal = mstr_signal * 0.6 + eth_signal * 0.4
            
            # Ensure result is finite
            if not np.isfinite(weighted_signal):
                return 0.0
            
            return float(np.clip(weighted_signal, -1, 1))
            
        except Exception as e:
            logger.error(f"Composite signal calculation error: {e}")
            return 0.0
    
    def _get_fallback_analysis(self) -> Dict:
        """Fallback when analysis fails"""
        return {
            'mstr': {
                'signals': [{
                    'type': 'error',
                    'message': '❌ MSTR data unavailable',
                    'action': 'Check connection',
                    'confidence': 0
                }]
            },
            'eth_btc': {
                'signals': [{
                    'type': 'error', 
                    'message': '❌ ETH/BTC data unavailable',
                    'action': 'Check connection',
                    'confidence': 0
                }]
            },
            'market_phase': {
                'phase': 'error',
                'message': 'Analysis unavailable',
                'confidence': 0
            },
            'composite_signal': 0,
            'last_updated': int(time.time())
        }


# Global instance
multi_asset_manager = None

async def get_multi_asset_manager(database: Database = None) -> MultiAssetCorrelationManager:
    """Get or create global multi-asset manager"""
    global multi_asset_manager
    
    if multi_asset_manager is None:
        if database is None:
            database = Database()
        multi_asset_manager = MultiAssetCorrelationManager(database)
    
    return multi_asset_manager