#!/usr/bin/env python3
"""
System Monitoring and Health Checks
Ensures system reliability and data quality
"""
import time
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import aiohttp
from database import Database
from config import VALIDATION_RULES, API_CONFIG

logger = logging.getLogger(__name__)

class SystemMonitor:
    """Monitor system health and data quality"""
    
    def __init__(self):
        self.db = Database()
        self.metrics = {
            'api_failures': {},
            'data_gaps': {},
            'response_times': {},
            'error_counts': {},
            'last_successful_fetch': {}
        }
        self.alerts = []
        
    async def health_check(self) -> Dict:
        """Comprehensive system health check"""
        health = {
            'status': 'healthy',
            'timestamp': int(time.time()),
            'checks': {},
            'alerts': []
        }
        
        # Check database
        health['checks']['database'] = await self._check_database()
        
        # Check API connectivity
        health['checks']['apis'] = await self._check_apis()
        
        # Check data freshness
        health['checks']['data_freshness'] = await self._check_data_freshness()
        
        # Check cache performance
        health['checks']['cache'] = self._check_cache()
        
        # Check for data gaps
        health['checks']['data_gaps'] = self._check_data_gaps()
        
        # Determine overall status
        if any(check.get('status') == 'critical' for check in health['checks'].values()):
            health['status'] = 'critical'
        elif any(check.get('status') == 'warning' for check in health['checks'].values()):
            health['status'] = 'degraded'
        
        # Add any active alerts
        health['alerts'] = self.alerts[-10:]  # Last 10 alerts
        
        return health
    
    async def _check_database(self) -> Dict:
        """Check database health"""
        try:
            with self.db.get_connection() as conn:
                # Check if database is accessible
                cursor = conn.execute("SELECT COUNT(*) FROM price_data")
                count = cursor.fetchone()[0]
                
                # Check database size
                cursor = conn.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
                db_size = cursor.fetchone()[0]
                
                # Check for recent data
                cursor = conn.execute("""
                    SELECT MAX(timestamp) as latest 
                    FROM price_data
                """)
                latest = cursor.fetchone()[0]
                
                age = int(time.time()) - latest if latest else float('inf')
                
                return {
                    'status': 'healthy' if age < 300 else 'warning',
                    'records': count,
                    'size_mb': round(db_size / 1024 / 1024, 2),
                    'latest_data_age': age,
                    'message': f"Database has {count:,} records, {round(db_size/1024/1024, 1)}MB"
                }
                
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                'status': 'critical',
                'error': str(e),
                'message': 'Database unavailable'
            }
    
    async def _check_apis(self) -> Dict:
        """Check API connectivity"""
        api_status = {}
        
        async with aiohttp.ClientSession() as session:
            # Check Binance
            try:
                url = f"{API_CONFIG['binance']['base_url']}/ping"
                start = time.time()
                async with session.get(url, timeout=5) as resp:
                    response_time = (time.time() - start) * 1000
                    api_status['binance'] = {
                        'status': 'healthy' if resp.status == 200 else 'warning',
                        'response_time_ms': round(response_time, 2)
                    }
            except Exception as e:
                api_status['binance'] = {'status': 'critical', 'error': str(e)}
            
            # Check Blockchain.info
            try:
                url = f"{API_CONFIG['blockchain_info']['base_url']}/latestblock"
                start = time.time()
                async with session.get(url, timeout=10) as resp:
                    response_time = (time.time() - start) * 1000
                    api_status['blockchain'] = {
                        'status': 'healthy' if resp.status == 200 else 'warning',
                        'response_time_ms': round(response_time, 2)
                    }
            except Exception as e:
                api_status['blockchain'] = {'status': 'degraded', 'error': str(e)}
        
        # Overall API status
        if all(api.get('status') == 'healthy' for api in api_status.values()):
            status = 'healthy'
        elif any(api.get('status') == 'critical' for api in api_status.values()):
            status = 'critical'
        else:
            status = 'degraded'
        
        return {
            'status': status,
            'apis': api_status,
            'message': f"{len([a for a in api_status.values() if a.get('status') == 'healthy'])}/{len(api_status)} APIs healthy"
        }
    
    async def _check_data_freshness(self) -> Dict:
        """Check if data is fresh"""
        try:
            with self.db.get_connection() as conn:
                checks = {}
                
                # Check BTC price freshness
                cursor = conn.execute("""
                    SELECT MAX(timestamp) as latest 
                    FROM price_data
                """)
                btc_latest = cursor.fetchone()[0]
                btc_age = int(time.time()) - btc_latest if btc_latest else float('inf')
                checks['btc_price'] = {
                    'age_seconds': btc_age,
                    'status': 'healthy' if btc_age < 60 else 'warning' if btc_age < 300 else 'critical'
                }
                
                # Check whale data freshness
                cursor = conn.execute("""
                    SELECT MAX(timestamp) as latest 
                    FROM whale_movements
                """)
                whale_latest = cursor.fetchone()[0]
                whale_age = int(time.time()) - whale_latest if whale_latest else float('inf')
                checks['whale_data'] = {
                    'age_seconds': whale_age,
                    'status': 'healthy' if whale_age < 3600 else 'warning'  # 1 hour for whale data
                }
                
                # Check MSTR data freshness
                cursor = conn.execute("""
                    SELECT MAX(timestamp) as latest 
                    FROM mstr_data
                """)
                mstr_latest = cursor.fetchone()[0]
                mstr_age = int(time.time()) - mstr_latest if mstr_latest else float('inf')
                checks['mstr_data'] = {
                    'age_seconds': mstr_age,
                    'status': 'healthy' if mstr_age < 1800 else 'warning'  # 30 min for MSTR
                }
                
                # Overall freshness
                if all(check.get('status') == 'healthy' for check in checks.values()):
                    status = 'healthy'
                elif any(check.get('status') == 'critical' for check in checks.values()):
                    status = 'critical'
                else:
                    status = 'warning'
                
                return {
                    'status': status,
                    'checks': checks,
                    'message': 'All data streams are fresh' if status == 'healthy' else 'Some data may be stale'
                }
                
        except Exception as e:
            logger.error(f"Data freshness check failed: {e}")
            return {'status': 'critical', 'error': str(e)}
    
    def _check_cache(self) -> Dict:
        """Check cache performance"""
        try:
            from cache_manager import get_cache_manager
            cache = get_cache_manager()
            stats = cache.get_stats()
            
            hit_rate = float(stats['hit_rate'].strip('%'))
            
            return {
                'status': 'healthy' if hit_rate > 70 else 'warning',
                'hit_rate': stats['hit_rate'],
                'memory_items': stats['memory_items'],
                'disk_files': stats['disk_files'],
                'message': f"Cache hit rate: {stats['hit_rate']}"
            }
        except Exception as e:
            return {'status': 'degraded', 'error': str(e)}
    
    def _check_data_gaps(self) -> Dict:
        """Check for data gaps in time series"""
        try:
            with self.db.get_connection() as conn:
                # Check for gaps in price data (should have data every minute)
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total,
                        (MAX(timestamp) - MIN(timestamp)) / 60 as expected_points
                    FROM price_data
                    WHERE timestamp > ?
                """, (int(time.time() - 3600),))  # Last hour
                
                result = cursor.fetchone()
                if result and result[1]:
                    actual = result[0]
                    expected = result[1]
                    gap_ratio = actual / expected if expected > 0 else 0
                    
                    return {
                        'status': 'healthy' if gap_ratio > 0.8 else 'warning',
                        'completeness': f"{gap_ratio*100:.1f}%",
                        'actual_points': actual,
                        'expected_points': int(expected),
                        'message': f"Data completeness: {gap_ratio*100:.1f}%"
                    }
                
                return {'status': 'warning', 'message': 'Unable to calculate data gaps'}
                
        except Exception as e:
            return {'status': 'degraded', 'error': str(e)}
    
    def add_alert(self, level: str, message: str, details: Optional[Dict] = None):
        """Add an alert to the system"""
        alert = {
            'timestamp': int(time.time()),
            'level': level,  # 'info', 'warning', 'critical'
            'message': message,
            'details': details or {}
        }
        self.alerts.append(alert)
        
        # Keep only last 100 alerts
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]
        
        # Log critical alerts
        if level == 'critical':
            logger.error(f"CRITICAL ALERT: {message}")
        elif level == 'warning':
            logger.warning(f"WARNING: {message}")
    
    async def monitor_data_quality(self):
        """Monitor data quality in real-time"""
        while True:
            try:
                # Check for anomalies
                with self.db.get_connection() as conn:
                    # Check for price anomalies
                    cursor = conn.execute("""
                        SELECT price, timestamp 
                        FROM price_data 
                        ORDER BY timestamp DESC 
                        LIMIT 2
                    """)
                    prices = cursor.fetchall()
                    
                    if len(prices) == 2:
                        current, previous = prices[0][0], prices[1][0]
                        change = abs((current - previous) / previous) if previous else 0
                        
                        # Alert on >5% instant change (likely bad data)
                        if change > 0.05:
                            self.add_alert(
                                'warning',
                                f'Large price movement detected: {change*100:.1f}%',
                                {'current': current, 'previous': previous}
                            )
                    
                    # Check for stale data
                    health = await self._check_data_freshness()
                    if health['status'] == 'critical':
                        self.add_alert('critical', 'Data feed appears to be down')
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Data quality monitoring error: {e}")
                await asyncio.sleep(60)

class RateLimiter:
    """Rate limiting for API calls"""
    
    def __init__(self):
        self.call_times = {}
        self.limits = API_CONFIG
    
    async def check_rate_limit(self, service: str) -> bool:
        """Check if we can make an API call"""
        if service not in self.limits:
            return True
        
        limit = self.limits[service].get('rate_limit')
        if not limit:
            return True  # No limit
        
        current_time = time.time()
        
        # Clean old entries
        if service in self.call_times:
            self.call_times[service] = [
                t for t in self.call_times[service] 
                if current_time - t < 60
            ]
        else:
            self.call_times[service] = []
        
        # Check if under limit
        if len(self.call_times[service]) < limit:
            self.call_times[service].append(current_time)
            return True
        
        return False
    
    async def wait_if_needed(self, service: str):
        """Wait if rate limited"""
        while not await self.check_rate_limit(service):
            await asyncio.sleep(1)

# Singleton instances
_monitor = None
_rate_limiter = None

def get_monitor() -> SystemMonitor:
    global _monitor
    if _monitor is None:
        _monitor = SystemMonitor()
    return _monitor

def get_rate_limiter() -> RateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter

if __name__ == "__main__":
    async def test():
        monitor = get_monitor()
        health = await monitor.health_check()
        
        print("🏥 SYSTEM HEALTH CHECK")
        print(f"Status: {health['status'].upper()}")
        print("\nChecks:")
        for check_name, check_data in health['checks'].items():
            status = check_data.get('status', 'unknown')
            message = check_data.get('message', '')
            symbol = '✅' if status == 'healthy' else '⚠️' if status == 'warning' else '❌'
            print(f"  {symbol} {check_name}: {message}")
        
        if health['alerts']:
            print("\nRecent Alerts:")
            for alert in health['alerts'][-5:]:
                print(f"  [{alert['level']}] {alert['message']}")
    
    asyncio.run(test())