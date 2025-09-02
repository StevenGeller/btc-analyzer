import asyncio
import json
import logging
from typing import Dict, Optional
from datetime import datetime
import time

from database import Database
# Commented out archived modules
# from websocket_streamer import BinanceWebSocketStreamer
# from liquidation_tracker import LiquidationTracker, LiquidationWebSocketMonitor
# from funding_tracker import FundingTracker, FundingMonitor
# from market_microstructure import MarketMicrostructureAnalyzer
from pattern_recognition import AdvancedPatternDetector

logger = logging.getLogger(__name__)

class MicrostructureManager:
    """
    Orchestrates all microstructure analysis components.
    This is what transforms your basic analyzer into a professional trading tool.
    """
    
    def __init__(self):
        self.db = Database()
        
        # Initialize available components
        self.pattern_detector = AdvancedPatternDetector(self.db)
        
        # Placeholder for archived components
        self.ws_streamer = None
        self.liquidation_tracker = None
        self.funding_tracker = None
        self.microstructure_analyzer = None
        self.liquidation_monitor = None
        self.funding_monitor = None
        
        # Real-time data cache
        self.current_analysis = {}
        self.last_update = 0
        
        # WebSocket callbacks for real-time updates
        self.ws_callbacks = []
        
    async def start_all_services(self):
        """Start all microstructure analysis services"""
        try:
            logger.info("Starting microstructure analysis system...")
            
            # Services are archived, just log
            logger.info("Pattern detection service available")
            
            # No services to start currently
            await asyncio.sleep(0.1)  # Small delay to avoid immediate return
            
        except Exception as e:
            logger.error(f"Error starting microstructure services: {e}")
            raise
    
    async def stop_all_services(self):
        """Stop all services gracefully"""
        try:
            await self.ws_streamer.stop()
            await self.liquidation_monitor.stop_monitoring()
            await self.funding_monitor.stop_monitoring()
            logger.info("All microstructure services stopped")
        except Exception as e:
            logger.error(f"Error stopping services: {e}")
    
    async def _on_order_flow_update(self, stream_name: str, data: dict):
        """Handle real-time order flow updates"""
        try:
            # Get order flow metrics from WebSocket streamer
            order_flow_metrics = self.ws_streamer.get_order_flow_metrics()
            
            if not order_flow_metrics.get('insufficient_data'):
                # Store in database
                self.db.store_order_flow_data(order_flow_metrics)
                
                # Store whale trades
                if hasattr(self.ws_streamer, 'order_flow_buffer'):
                    recent_trades = self.ws_streamer.order_flow_buffer[-10:]  # Last 10 trades
                    for trade in recent_trades:
                        trade_size = self.ws_streamer._classify_trade_size(trade['value'])
                        if trade_size == 'whale':
                            whale_trade_data = {
                                'timestamp': trade['timestamp'],
                                'price': trade['price'],
                                'quantity': trade['quantity'],
                                'value_usd': trade['value'],
                                'is_market_buy': trade['is_market_buy'],
                                'trade_size_category': 'whale',
                                'trade_id': trade.get('trade_id')
                            }
                            self.db.store_whale_trade(whale_trade_data)
                
                # Trigger analysis update
                await self._update_analysis()
                
        except Exception as e:
            logger.error(f"Order flow update error: {e}")
    
    async def _update_analysis(self):
        """Update comprehensive microstructure analysis"""
        try:
            current_time = time.time()
            
            # Don't update too frequently (max every 5 seconds)
            if current_time - self.last_update < 5:
                return
            
            # Get comprehensive analysis
            microstructure_summary = await self.microstructure_analyzer.get_microstructure_summary()
            pattern_analysis = await self.pattern_detector.get_all_patterns()
            funding_analysis = await self.funding_tracker.analyze_funding_sentiment()
            
            # Store the current analysis
            self.current_analysis = {
                'timestamp': current_time,
                'microstructure': microstructure_summary,
                'patterns': pattern_analysis,
                'funding': funding_analysis,
                'order_flow': microstructure_summary.get('order_flow', {}),
                'liquidations': microstructure_summary.get('liquidations', {}),
                'absorption': microstructure_summary.get('absorption', {}),
                'last_updated': datetime.now().isoformat()
            }
            
            self.last_update = current_time
            
            # Notify WebSocket clients
            await self._notify_websocket_clients()
            
            logger.debug("Microstructure analysis updated")
            
        except Exception as e:
            logger.error(f"Analysis update error: {e}")
    
    async def _notify_websocket_clients(self):
        """Notify all WebSocket clients of analysis updates"""
        if not self.ws_callbacks:
            return
        
        message = {
            'type': 'microstructure_update',
            'data': self.current_analysis
        }
        
        # Send to all registered callbacks
        for callback in self.ws_callbacks[:]:  # Copy list to avoid modification during iteration
            try:
                await callback(message)
            except Exception as e:
                logger.error(f"WebSocket callback error: {e}")
                # Remove failed callback
                self.ws_callbacks.remove(callback)
    
    def register_websocket_callback(self, callback):
        """Register WebSocket callback for real-time updates"""
        self.ws_callbacks.append(callback)
        logger.debug("WebSocket callback registered")
    
    def unregister_websocket_callback(self, callback):
        """Unregister WebSocket callback"""
        if callback in self.ws_callbacks:
            self.ws_callbacks.remove(callback)
            logger.debug("WebSocket callback unregistered")
    
    async def get_current_analysis(self) -> Dict:
        """Get current microstructure analysis"""
        if not self.current_analysis or time.time() - self.last_update > 30:
            # Force update if data is stale
            await self._update_analysis()
        
        return self.current_analysis
    
    async def get_enhanced_price_data(self) -> Dict:
        """Get current Bitcoin price with microstructure context"""
        try:
            # Get latest price from working analyzer (fallback to Binance API)
            from working_app import working_analyzer
            
            basic_data = await working_analyzer.get_real_bitcoin_data()
            current_analysis = await self.get_current_analysis()
            
            # Enhance with microstructure insights
            enhanced_data = basic_data.copy()
            
            if current_analysis.get('microstructure'):
                ms = current_analysis['microstructure']
                enhanced_data['microstructure_signal'] = ms.get('overall_signal', 0)
                enhanced_data['microstructure_confidence'] = ms.get('overall_confidence', 0)
                enhanced_data['action_message'] = ms.get('action_message', '')
            
            if current_analysis.get('patterns', {}).get('active_patterns'):
                enhanced_data['active_patterns'] = len(current_analysis['patterns']['active_patterns'])
                enhanced_data['pattern_signals'] = [
                    p['pattern'].get('message', '') 
                    for p in current_analysis['patterns']['active_patterns']
                ]
            
            if current_analysis.get('liquidations'):
                liq = current_analysis['liquidations']
                enhanced_data['liquidation_risk'] = liq.get('cascade_risk', 'low')
                enhanced_data['liquidation_direction'] = liq.get('direction', 'balanced')
            
            return enhanced_data
            
        except Exception as e:
            logger.error(f"Enhanced price data error: {e}")
            # Fallback to basic data
            from working_app import working_analyzer
            return await working_analyzer.get_real_bitcoin_data()
    
    async def get_microstructure_dashboard_data(self) -> Dict:
        """Get data specifically formatted for the professional dashboard"""
        try:
            current_analysis = await self.get_current_analysis()
            price_data = await self.get_enhanced_price_data()
            
            # Format for dashboard consumption
            dashboard_data = {
                'price': price_data.get('current_data', {}).get('price', 0),
                'timestamp': int(time.time()),
                
                # Order flow data
                'order_flow': current_analysis.get('order_flow', {
                    'signal': 0,
                    'confidence': 0,
                    'delta': 0,
                    'cumulative_delta': 0,
                    'whale_bias': 0,
                    'aggression_score': 0,
                    'volume_imbalance': 0,
                    'interpretation': 'No data available'
                }),
                
                # Microstructure metrics
                'microstructure': {
                    'overall_signal': current_analysis.get('microstructure', {}).get('overall_signal', 0),
                    'overall_confidence': current_analysis.get('microstructure', {}).get('overall_confidence', 0),
                    'aggression_score': current_analysis.get('order_flow', {}).get('aggression_score', 0),
                    'volume_imbalance': current_analysis.get('order_flow', {}).get('volume_imbalance', 0),
                    'market_pressure': self._calculate_market_pressure(current_analysis),
                    'institutional_flow': current_analysis.get('order_flow', {}).get('whale_bias', 0)
                },
                
                # Pattern analysis
                'patterns': current_analysis.get('patterns', {
                    'wyckoff': {'phase': 'unknown', 'confidence': 0},
                    'stop_hunt': {'stop_hunt': False},
                    'divergence': {'divergence': None},
                    'active_patterns': []
                }),
                
                # Liquidation analysis
                'liquidations': current_analysis.get('liquidations', {
                    'cascade_risk': 'low',
                    'risk_score': 0,
                    'message': 'No liquidation data'
                }),
                
                # Absorption analysis
                'absorption': current_analysis.get('absorption', {
                    'absorption': None,
                    'message': 'No absorption detected'
                }),
                
                # Whale activity (recent whale trades)
                'whale_activity': self._get_recent_whale_activity(),
                
                # Funding data
                'funding': current_analysis.get('funding', {
                    'sentiment': 'neutral',
                    'weighted_funding_rate': 0,
                    'message': 'No funding data'
                })
            }
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Dashboard data error: {e}")
            return self._get_fallback_dashboard_data()
    
    def _calculate_market_pressure(self, analysis: Dict) -> float:
        """Calculate overall market pressure from various signals"""
        try:
            order_flow_signal = analysis.get('order_flow', {}).get('signal', 0)
            liquidation_signal = 0
            
            # Convert liquidation data to pressure signal
            liquidations = analysis.get('liquidations', {})
            if liquidations.get('direction') == 'upward_pressure':
                liquidation_signal = 0.5  # Shorts being squeezed = bullish pressure
            elif liquidations.get('direction') == 'downward_pressure':
                liquidation_signal = -0.5  # Longs being liquidated = bearish pressure
            
            # Funding pressure
            funding_signal = 0
            funding = analysis.get('funding', {})
            if funding.get('sentiment') == 'extremely_bullish':
                funding_signal = -0.3  # High funding = bearish for price
            elif funding.get('sentiment') == 'extremely_bearish':
                funding_signal = 0.3  # Low/negative funding = bullish for price
            
            # Combined pressure
            pressure = (order_flow_signal * 0.6 + liquidation_signal * 0.3 + funding_signal * 0.1)
            return max(-1.0, min(1.0, pressure))
            
        except Exception:
            return 0.0
    
    def _get_recent_whale_activity(self) -> list:
        """Get recent whale trades for display"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT price, quantity, value_usd, is_market_buy, timestamp
                    FROM whale_trades
                    WHERE timestamp > ?
                    ORDER BY timestamp DESC
                    LIMIT 10
                """, (int(time.time() - 3600),))  # Last hour
                
                trades = cursor.fetchall()
            
            return [
                {
                    'price': float(t['price']),
                    'quantity': float(t['quantity']),
                    'value': float(t['value_usd']),
                    'is_buy': bool(t['is_market_buy']),
                    'timestamp': int(t['timestamp'])
                }
                for t in trades
            ]
            
        except Exception as e:
            logger.error(f"Whale activity error: {e}")
            return []
    
    def _get_fallback_dashboard_data(self) -> Dict:
        """Fallback data when analysis fails"""
        return {
            'price': 0,
            'timestamp': int(time.time()),
            'order_flow': {
                'signal': 0, 'confidence': 0, 'delta': 0,
                'cumulative_delta': 0, 'whale_bias': 0,
                'interpretation': 'Analysis temporarily unavailable'
            },
            'microstructure': {
                'overall_signal': 0, 'overall_confidence': 0,
                'aggression_score': 0, 'volume_imbalance': 0,
                'market_pressure': 0, 'institutional_flow': 0
            },
            'patterns': {
                'wyckoff': {'phase': 'unknown', 'confidence': 0},
                'stop_hunt': {'stop_hunt': False},
                'divergence': {'divergence': None},
                'active_patterns': []
            },
            'liquidations': {
                'cascade_risk': 'unknown',
                'risk_score': 0,
                'message': 'Analysis unavailable'
            },
            'absorption': {
                'absorption': None,
                'message': 'Analysis unavailable'
            },
            'whale_activity': [],
            'funding': {
                'sentiment': 'unknown',
                'weighted_funding_rate': 0,
                'message': 'Analysis unavailable'
            }
        }
    
    async def cleanup_old_data(self):
        """Clean up old microstructure data periodically"""
        try:
            self.db.cleanup_old_microstructure_data(days=7)
            logger.info("Microstructure data cleanup completed")
        except Exception as e:
            logger.error(f"Data cleanup error: {e}")

# Global instance
microstructure_manager = None

async def get_microstructure_manager():
    """Get or create the global microstructure manager"""
    global microstructure_manager
    
    if microstructure_manager is None:
        microstructure_manager = MicrostructureManager()
        # Start services in background
        asyncio.create_task(microstructure_manager.start_all_services())
    
    return microstructure_manager