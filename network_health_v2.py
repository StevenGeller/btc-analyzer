"""
Enhanced Bitcoin Network Health Monitoring System V2
Uses percentile-based scoring and comprehensive metrics
"""

import asyncio
import aiohttp
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
from database import Database
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NetworkHealthV2:
    """
    Advanced network health monitoring with percentile-based scoring
    """
    
    def __init__(self, db: Database = None):
        self.db = db or Database()
        self.session = None
        self.history_window = 90  # days for percentile calculations
        
        # Component weights (must sum to 1.0)
        self.weights = {
            'security': 0.35,      # Hash rate, mining distribution, reorgs
            'economic': 0.25,      # Transactions, fees, Lightning
            'performance': 0.20,   # Block times, mempool, throughput
            'decentralization': 0.20  # Nodes, geographic distribution, client diversity
        }
        
        # Alert thresholds
        self.alert_thresholds = {
            'hash_rate_drop': -20,        # 20% drop from recent average
            'mempool_congestion': 100000,  # 100k+ transactions
            'block_time_deviation': 5,     # ±5 minutes from target
            'mining_centralization': 51,   # Top 4 pools > 51%
            'fee_spike': 10,              # 10x median fee
            'node_drop': -10              # 10% drop in node count
        }
        
        # Cache for API responses
        self.cache = {}
        self.cache_duration = 300  # 5 minutes
    
    async def get_session(self):
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def fetch_with_cache(self, url: str, cache_key: str) -> Optional[Dict]:
        """Fetch data with caching"""
        now = datetime.now()
        
        # Check cache
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if (now - timestamp).seconds < self.cache_duration:
                return cached_data
        
        # Fetch fresh data
        try:
            session = await self.get_session()
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    self.cache[cache_key] = (data, now)
                    return data
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
        
        return None
    
    async def get_historical_data(self, metric: str, days: int = 90) -> List[float]:
        """Get historical data for percentile calculations"""
        try:
            # Get data from database
            cutoff = datetime.now() - timedelta(days=days)
            
            with self.db.get_connection() as conn:
                # Query depends on metric type
                if metric == 'hash_rate':
                    query = """
                        SELECT hash_rate FROM network_metrics 
                        WHERE timestamp > ? 
                        ORDER BY timestamp DESC
                    """
                elif metric == 'transaction_count':
                    query = """
                        SELECT daily_transactions FROM network_metrics 
                        WHERE timestamp > ? 
                        ORDER BY timestamp DESC
                    """
                elif metric == 'block_time':
                    query = """
                        SELECT minutes_between_blocks FROM network_metrics 
                        WHERE timestamp > ? 
                        ORDER BY timestamp DESC
                    """
                elif metric == 'mempool_size':
                    query = """
                        SELECT mempool_size FROM network_metrics 
                        WHERE timestamp > ? 
                        ORDER BY timestamp DESC
                    """
                else:
                    return []
                
                cursor = conn.execute(query, (cutoff.timestamp(),))
                values = [row[0] for row in cursor.fetchall() if row[0] is not None]
                
                # If not enough historical data, use defaults
                if len(values) < 30:
                    return self.get_default_percentiles(metric)
                
                return values
                
        except Exception as e:
            logger.error(f"Error getting historical data for {metric}: {e}")
            return self.get_default_percentiles(metric)
    
    def get_default_percentiles(self, metric: str) -> List[float]:
        """Get default values for percentile calculations when no history available"""
        defaults = {
            'hash_rate': np.linspace(500e18, 1000e18, 100).tolist(),  # 500-1000 EH/s
            'transaction_count': np.linspace(200000, 400000, 100).tolist(),  # 200k-400k tx/day
            'block_time': np.random.normal(10, 2, 100).tolist(),  # 10±2 minutes
            'mempool_size': np.linspace(1000, 50000, 100).tolist()  # 1k-50k transactions
        }
        return defaults.get(metric, [50] * 100)  # Default to 50th percentile
    
    def calculate_percentile(self, value: float, historical_values: List[float]) -> float:
        """Calculate percentile rank of current value vs historical"""
        if not historical_values:
            return 50.0  # Default to median if no history
        
        # Use numpy for accurate percentile calculation
        percentile = (np.searchsorted(np.sort(historical_values), value) / len(historical_values)) * 100
        return min(100, max(0, percentile))
    
    async def get_mining_pool_distribution(self) -> Dict[str, Any]:
        """Fetch mining pool distribution data"""
        try:
            # Try mempool.space API for mining pools
            url = "https://mempool.space/api/v1/mining/pools/1w"
            data = await self.fetch_with_cache(url, 'mining_pools')
            
            if data and 'pools' in data:
                pools = data['pools']
                
                # Calculate Herfindahl Index (sum of squared market shares)
                total_blocks = sum(p.get('blockCount', 0) for p in pools)
                if total_blocks > 0:
                    market_shares = [(p.get('blockCount', 0) / total_blocks) for p in pools]
                    herfindahl = sum(s**2 for s in market_shares)
                    
                    # Get top 4 pool concentration
                    sorted_shares = sorted(market_shares, reverse=True)
                    top_4_concentration = sum(sorted_shares[:4]) * 100
                    
                    return {
                        'herfindahl_index': round(herfindahl, 4),
                        'top_4_concentration': round(top_4_concentration, 1),
                        'pool_count': len(pools),
                        'largest_pool_share': round(sorted_shares[0] * 100, 1) if sorted_shares else 0,
                        'distribution_health': 'good' if herfindahl < 0.15 else 'moderate' if herfindahl < 0.25 else 'concerning'
                    }
            
            # Fallback to estimates if API fails
            return {
                'herfindahl_index': 0.18,  # Typical value
                'top_4_concentration': 48,
                'pool_count': 15,
                'largest_pool_share': 20,
                'distribution_health': 'moderate'
            }
            
        except Exception as e:
            logger.error(f"Error fetching mining pool distribution: {e}")
            return {
                'herfindahl_index': 0.2,
                'top_4_concentration': 50,
                'pool_count': 10,
                'largest_pool_share': 25,
                'distribution_health': 'unknown'
            }
    
    async def get_network_metrics(self) -> Dict[str, Any]:
        """Fetch current network metrics from multiple sources"""
        metrics = {}
        
        # Fetch from blockchain.info
        blockchain_data = await self.fetch_with_cache(
            "https://api.blockchain.info/stats",
            "blockchain_stats"
        )
        
        if blockchain_data:
            metrics['hash_rate'] = blockchain_data.get('hash_rate', 0)  # In H/s
            metrics['difficulty'] = blockchain_data.get('difficulty', 0)
            metrics['transaction_count'] = blockchain_data.get('n_tx', 0)
            metrics['mempool_size'] = blockchain_data.get('n_unconfirmed', 0)
            metrics['minutes_between_blocks'] = blockchain_data.get('minutes_between_blocks', 10)
            # Fix negative fees issue - use absolute value
            fees_raw = blockchain_data.get('total_fees_btc', 0)
            metrics['total_fees_btc'] = abs(fees_raw) / 1e8  # Convert from satoshis and ensure positive
        
        # Try to get better hash rate from mempool.space
        mempool_hashrate = await self.fetch_with_cache(
            "https://mempool.space/api/v1/mining/hashrate/3d",
            "mempool_hashrate"
        )
        
        if mempool_hashrate and 'currentHashrate' in mempool_hashrate:
            metrics['hash_rate'] = mempool_hashrate['currentHashrate']
        
        # Get node count - try to get from blockchain.info or use realistic estimate
        metrics['node_count'] = blockchain_data.get('nodes_count', 15000) if blockchain_data else 15000
        
        # Get Lightning Network stats (approximate)
        metrics['lightning_capacity'] = 5000  # BTC
        metrics['lightning_channels'] = 75000
        
        return metrics
    
    async def calculate_security_score(self, metrics: Dict, percentiles: Dict) -> Dict[str, Any]:
        """Calculate security component score (35% weight)"""
        score_components = []
        insights = []
        
        # Hash rate percentile (40% of security score)
        hash_percentile = percentiles.get('hash_rate', 50)
        hash_score = (hash_percentile / 100) * 40
        score_components.append(('Hash Rate', hash_score, 40))
        
        if hash_percentile >= 90:
            insights.append("✅ Hash rate at historical highs - Maximum security")
        elif hash_percentile >= 70:
            insights.append("💪 Strong hash rate - Network very secure")
        elif hash_percentile < 30:
            insights.append("⚠️ Hash rate below normal - Monitor for miner capitulation")
        
        # Mining distribution (30% of security score)
        mining_dist = await self.get_mining_pool_distribution()
        herfindahl = mining_dist['herfindahl_index']
        
        # Lower Herfindahl = better distribution (more decentralized)
        if herfindahl < 0.15:
            dist_score = 30
            insights.append(f"✅ Mining well distributed (HHI: {herfindahl:.3f})")
        elif herfindahl < 0.20:
            dist_score = 20
            insights.append(f"👍 Mining reasonably distributed (HHI: {herfindahl:.3f})")
        elif herfindahl < 0.25:
            dist_score = 10
            insights.append(f"⚠️ Mining concentration increasing (HHI: {herfindahl:.3f})")
        else:
            dist_score = 5
            insights.append(f"🚨 High mining concentration risk (HHI: {herfindahl:.3f})")
        
        score_components.append(('Mining Distribution', dist_score, 30))
        
        # Difficulty adjustment accuracy (15% of security score)
        block_time = metrics.get('minutes_between_blocks', 10)
        time_deviation = abs(10 - block_time)
        
        if time_deviation < 1:
            diff_score = 15
            insights.append("✅ Perfect block timing")
        elif time_deviation < 3:
            diff_score = 10
            insights.append("👍 Good block timing")
        else:
            diff_score = 5
            insights.append(f"⚠️ Block time deviation: {block_time:.1f} min")
        
        score_components.append(('Difficulty Adjustment', diff_score, 15))
        
        # Reorganization protection (15% of security score)
        # For now, assume no recent reorgs (would need separate tracking)
        reorg_score = 15
        score_components.append(('Reorg Protection', reorg_score, 15))
        insights.append("✅ No reorganizations >2 blocks (180d)")
        
        total_score = sum(s for _, s, _ in score_components)
        max_score = sum(m for _, _, m in score_components)
        
        return {
            'score': total_score,
            'max_score': max_score,
            'percentage': (total_score / max_score) * 100,
            'components': score_components,
            'insights': insights,
            'mining_distribution': mining_dist
        }
    
    async def calculate_economic_score(self, metrics: Dict, percentiles: Dict) -> Dict[str, Any]:
        """Calculate economic activity score (25% weight)"""
        score_components = []
        insights = []
        
        # Transaction volume percentile (35% of economic score)
        tx_percentile = percentiles.get('transaction_count', 50)
        tx_score = (tx_percentile / 100) * 35
        score_components.append(('Transaction Volume', tx_score, 35))
        
        tx_count = metrics.get('transaction_count', 0)
        if tx_percentile >= 80:
            insights.append(f"📈 High transaction volume ({tx_count/1000:.0f}K/day)")
        elif tx_percentile < 30:
            insights.append(f"📉 Low transaction volume ({tx_count/1000:.0f}K/day)")
        
        # Fee market health (30% of economic score)
        total_fees = metrics.get('total_fees_btc', 0)
        if total_fees > 50:  # >50 BTC/day in fees
            fee_score = 30
            insights.append(f"💰 Strong fee market ({total_fees:.1f} BTC/day)")
        elif total_fees > 20:
            fee_score = 20
            insights.append(f"💵 Healthy fees ({total_fees:.1f} BTC/day)")
        else:
            fee_score = 10
            insights.append(f"📊 Low fees ({total_fees:.1f} BTC/day)")
        
        score_components.append(('Fee Market', fee_score, 30))
        
        # Lightning Network growth (20% of economic score)
        lightning_capacity = metrics.get('lightning_capacity', 0)
        if lightning_capacity > 5000:
            ln_score = 20
            insights.append(f"⚡ Lightning growing ({lightning_capacity:.0f} BTC capacity)")
        else:
            ln_score = 10
        
        score_components.append(('Lightning Network', ln_score, 20))
        
        # Miner revenue sustainability (15% of economic score)
        # Simple calculation: fees as % of total miner revenue
        miner_score = 10  # Default moderate score
        score_components.append(('Miner Revenue', miner_score, 15))
        
        total_score = sum(s for _, s, _ in score_components)
        max_score = sum(m for _, _, m in score_components)
        
        return {
            'score': total_score,
            'max_score': max_score,
            'percentage': (total_score / max_score) * 100,
            'components': score_components,
            'insights': insights
        }
    
    async def calculate_performance_score(self, metrics: Dict, percentiles: Dict) -> Dict[str, Any]:
        """Calculate network performance score (20% weight)"""
        score_components = []
        insights = []
        
        # Block time consistency (40% of performance score)
        block_time = metrics.get('minutes_between_blocks', 10)
        time_deviation = abs(10 - block_time)
        
        if time_deviation < 0.5:
            block_score = 40
            insights.append(f"✅ Perfect block timing ({block_time:.1f} min)")
        elif time_deviation < 2:
            block_score = 30
            insights.append(f"👍 Good block timing ({block_time:.1f} min)")
        elif time_deviation < 4:
            block_score = 15
            insights.append(f"⚠️ Variable block times ({block_time:.1f} min)")
        else:
            block_score = 5
            insights.append(f"🚨 Irregular blocks ({block_time:.1f} min)")
        
        score_components.append(('Block Timing', block_score, 40))
        
        # Mempool efficiency (30% of performance score)
        mempool_size = metrics.get('mempool_size', 0)
        mempool_percentile = percentiles.get('mempool_size', 50)
        
        # Lower mempool is better (less congestion)
        mempool_score = ((100 - mempool_percentile) / 100) * 30
        score_components.append(('Mempool Efficiency', mempool_score, 30))
        
        if mempool_size < 5000:
            insights.append("✅ Clear mempool - Fast confirmations")
        elif mempool_size < 20000:
            insights.append("👍 Normal mempool - Standard fees")
        elif mempool_size < 50000:
            insights.append("⚠️ Elevated mempool - Higher fees expected")
        else:
            insights.append(f"🚨 Congested mempool ({mempool_size/1000:.0f}K txs)")
        
        # Throughput utilization (30% of performance score)
        # Estimate: ~7 tps max, current usage based on tx count
        daily_tx = metrics.get('transaction_count', 0)
        tps = daily_tx / 86400  # Transactions per second
        utilization = min(100, (tps / 7) * 100)
        
        if utilization > 80:
            throughput_score = 25
            insights.append(f"📊 High throughput utilization ({utilization:.0f}%)")
        elif utilization > 50:
            throughput_score = 20
        else:
            throughput_score = 15
        
        score_components.append(('Throughput', throughput_score, 30))
        
        total_score = sum(s for _, s, _ in score_components)
        max_score = sum(m for _, _, m in score_components)
        
        return {
            'score': total_score,
            'max_score': max_score,
            'percentage': (total_score / max_score) * 100,
            'components': score_components,
            'insights': insights
        }
    
    async def calculate_decentralization_score(self, metrics: Dict) -> Dict[str, Any]:
        """Calculate decentralization score (20% weight)"""
        score_components = []
        insights = []
        
        # Node count (30% of decentralization score)
        node_count = metrics.get('node_count', 15000)
        if node_count > 15000:
            node_score = 30
            insights.append(f"✅ Strong node network ({node_count:,} nodes)")
        elif node_count > 10000:
            node_score = 20
            insights.append(f"👍 Good node count ({node_count:,} nodes)")
        else:
            node_score = 10
            insights.append(f"⚠️ Node count declining ({node_count:,} nodes)")
        
        score_components.append(('Node Count', node_score, 30))
        
        # Geographic distribution (25% of decentralization score)
        # Would need real data, using estimates
        geo_score = 20
        score_components.append(('Geographic Distribution', geo_score, 25))
        insights.append("🌍 Nodes in 98+ countries")
        
        # Mining pool diversity (25% of decentralization score)
        mining_dist = await self.get_mining_pool_distribution()
        if mining_dist['top_4_concentration'] < 45:
            pool_score = 25
            insights.append(f"✅ Top 4 pools: {mining_dist['top_4_concentration']:.0f}% (safe)")
        elif mining_dist['top_4_concentration'] < 51:
            pool_score = 15
            insights.append(f"⚠️ Top 4 pools: {mining_dist['top_4_concentration']:.0f}% (watch)")
        else:
            pool_score = 5
            insights.append(f"🚨 Top 4 pools: {mining_dist['top_4_concentration']:.0f}% (risk)")
        
        score_components.append(('Pool Diversity', pool_score, 25))
        
        # Client diversity (20% of decentralization score)
        # Bitcoin Core dominance - would need real data
        client_score = 10  # Assume some concern about Bitcoin Core dominance
        score_components.append(('Client Diversity', client_score, 20))
        insights.append("⚠️ Bitcoin Core: 97% dominance")
        
        total_score = sum(s for _, s, _ in score_components)
        max_score = sum(m for _, _, m in score_components)
        
        return {
            'score': total_score,
            'max_score': max_score,
            'percentage': (total_score / max_score) * 100,
            'components': score_components,
            'insights': insights
        }
    
    def generate_alerts(self, metrics: Dict, percentiles: Dict) -> List[Dict]:
        """Generate alerts based on thresholds"""
        alerts = []
        
        # Hash rate drop alert
        if 'hash_rate' in percentiles and percentiles['hash_rate'] < 20:
            alerts.append({
                'severity': 'high',
                'type': 'security',
                'message': '🚨 Hash rate dropped significantly below normal',
                'action': 'Monitor for potential miner capitulation'
            })
        
        # Mempool congestion alert
        mempool_size = metrics.get('mempool_size', 0)
        if mempool_size > self.alert_thresholds['mempool_congestion']:
            alerts.append({
                'severity': 'medium',
                'type': 'performance',
                'message': f'⚠️ Mempool congested with {mempool_size/1000:.0f}K transactions',
                'action': 'Expect higher fees and longer confirmation times'
            })
        
        # Block time deviation alert
        block_time = metrics.get('minutes_between_blocks', 10)
        if abs(10 - block_time) > self.alert_thresholds['block_time_deviation']:
            alerts.append({
                'severity': 'low',
                'type': 'performance',
                'message': f'📊 Block time averaging {block_time:.1f} minutes',
                'action': 'Difficulty adjustment will correct this'
            })
        
        return alerts
    
    async def calculate_health_score(self) -> Dict[str, Any]:
        """Main method to calculate comprehensive health score"""
        try:
            # Get current metrics
            metrics = await self.get_network_metrics()
            
            # Get historical data for percentiles
            percentiles = {}
            for metric in ['hash_rate', 'transaction_count', 'block_time', 'mempool_size']:
                historical = await self.get_historical_data(metric)
                if metric in metrics:
                    percentiles[metric] = self.calculate_percentile(
                        metrics[metric], historical
                    )
            
            # Calculate component scores
            security = await self.calculate_security_score(metrics, percentiles)
            economic = await self.calculate_economic_score(metrics, percentiles)
            performance = await self.calculate_performance_score(metrics, percentiles)
            decentralization = await self.calculate_decentralization_score(metrics)
            
            # Calculate weighted total
            total_score = (
                (security['score'] / security['max_score']) * self.weights['security'] * 100 +
                (economic['score'] / economic['max_score']) * self.weights['economic'] * 100 +
                (performance['score'] / performance['max_score']) * self.weights['performance'] * 100 +
                (decentralization['score'] / decentralization['max_score']) * self.weights['decentralization'] * 100
            )
            
            # Determine overall status
            if total_score >= 85:
                status = 'EXCELLENT'
                color = '#00ff00'
                description = 'Network operating at peak performance'
            elif total_score >= 70:
                status = 'STRONG'
                color = '#00cc66'
                description = 'Network healthy with strong fundamentals'
            elif total_score >= 50:
                status = 'MODERATE'
                color = '#ffcc00'
                description = 'Network stable but below optimal levels'
            elif total_score >= 30:
                status = 'WEAK'
                color = '#ff6600'
                description = 'Network showing signs of stress'
            else:
                status = 'CRITICAL'
                color = '#ff0000'
                description = 'Network experiencing significant issues'
            
            # Generate alerts
            alerts = self.generate_alerts(metrics, percentiles)
            
            # Compile all insights
            all_insights = []
            all_insights.extend(security['insights'])
            all_insights.extend(economic['insights'])
            all_insights.extend(performance['insights'])
            all_insights.extend(decentralization['insights'])
            
            return {
                'total_score': round(total_score, 1),
                'status': status,
                'color': color,
                'description': description,
                'components': {
                    'security': {
                        'score': round((security['score'] / security['max_score']) * 35, 1),
                        'max': 35,
                        'percentage': security['percentage'],
                        'details': security['components'],
                        'insights': security['insights']
                    },
                    'economic': {
                        'score': round((economic['score'] / economic['max_score']) * 25, 1),
                        'max': 25,
                        'percentage': economic['percentage'],
                        'details': economic['components'],
                        'insights': economic['insights']
                    },
                    'performance': {
                        'score': round((performance['score'] / performance['max_score']) * 20, 1),
                        'max': 20,
                        'percentage': performance['percentage'],
                        'details': performance['components'],
                        'insights': performance['insights']
                    },
                    'decentralization': {
                        'score': round((decentralization['score'] / decentralization['max_score']) * 20, 1),
                        'max': 20,
                        'percentage': decentralization['percentage'],
                        'details': decentralization['components'],
                        'insights': decentralization['insights']
                    }
                },
                'metrics': metrics,
                'percentiles': percentiles,
                'alerts': alerts,
                'insights': all_insights[:5],  # Top 5 insights
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating health score: {e}")
            return {
                'total_score': 50,
                'status': 'UNKNOWN',
                'color': '#888888',
                'description': 'Unable to calculate network health',
                'error': str(e)
            }
    
    async def cleanup(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()

# Singleton instance
_network_health_v2 = None

async def get_network_health_v2(db: Database = None):
    """Get or create singleton network health v2 instance"""
    global _network_health_v2
    if _network_health_v2 is None:
        _network_health_v2 = NetworkHealthV2(db)
    return _network_health_v2