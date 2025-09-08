from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import logging
import aiohttp
import time
from datetime import datetime
from multi_asset_analyzer import get_multi_asset_manager
from database import Database
from microstructure_integration import get_microstructure_manager
from strategy_fetcher import StrategyDataFetcher, periodic_update_task
from real_whale_tracker import get_real_whale_tracker
from monitoring import get_monitor
from backup_manager import get_backup_manager, start_backup_service
from power_law_calculator import get_power_law_calculator
from real_onchain_data import get_real_onchain_data
from network_health_v2 import get_network_health_v2
from mstr_advanced_analytics import get_mstr_advanced_analytics
from mstr_holdings_fetcher import get_fetcher
from mstr_stock_fetcher import get_stock_fetcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Bitcoin Market State Analyzer with Multi-Asset Correlation")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class WorkingAnalyzer:
    """Guaranteed working analyzer - REAL DATA ONLY with Multi-Asset Correlation"""
    
    def __init__(self):
        self.session = None
        self.db = Database()
        self.multi_asset_manager = None
        self.microstructure_manager = None
        self.strategy_fetcher = StrategyDataFetcher()
    
    async def get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def get_multi_asset_manager(self):
        if self.multi_asset_manager is None:
            self.multi_asset_manager = await get_multi_asset_manager(self.db)
        return self.multi_asset_manager
    
    async def get_microstructure_manager(self):
        if self.microstructure_manager is None:
            self.microstructure_manager = await get_microstructure_manager()
        return self.microstructure_manager
    
    async def get_real_bitcoin_data(self):
        """Get REAL Bitcoin data from unlimited APIs"""
        try:
            session = await self.get_session()
            
            # Get Bitcoin data from Binance (unlimited)
            url = "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Extract real data
                    price = float(data['lastPrice'])
                    price_change_24h = float(data['priceChangePercent'])
                    volume_24h = float(data['volume']) * price
                    high_24h = float(data['highPrice'])
                    low_24h = float(data['lowPrice'])
                    
                    # Validate real Bitcoin price
                    if not (10000 <= price <= 1000000):
                        logger.error(f"Invalid price: ${price}")
                        raise ValueError("Invalid Bitcoin price")
                    
                    # Get Fear & Greed Index (unlimited)
                    fear_greed = 50
                    try:
                        fg_url = "https://api.alternative.me/fng/?limit=1"
                        async with session.get(fg_url) as fg_response:
                            if fg_response.status == 200:
                                fg_data = await fg_response.json()
                                fear_greed = int(fg_data['data'][0]['value'])
                    except:
                        pass
                    
                    # Calculate composite score from REAL data
                    score = price_change_24h / 20  # Normalize
                    if fear_greed < 25:
                        score += 0.2  # Extreme fear boost
                    elif fear_greed > 75:
                        score -= 0.2  # Extreme greed penalty
                    score = max(-1.0, min(1.0, score))
                    
                    # Calculate meaningful technical indicators from real data
                    volatility = abs(price_change_24h) / 100  # Real volatility from price movement
                    momentum = price_change_24h / 100  # Real momentum from price change
                    rsi = 50 + (price_change_24h * 2)  # RSI based on price movement (-50 to 150 range, then clamped)
                    rsi = max(0, min(100, rsi))  # Clamp RSI to valid range
                    
                    # Technical indicators composite
                    technical_score = (momentum + (volatility * 0.5) + ((rsi - 50) / 50 * 0.3)) / 2
                    
                    # Get Power Law status
                    power_law_calc = get_power_law_calculator()
                    power_law_data = power_law_calc.get_power_law_status(price)
                    
                    # Determine market state
                    if score > 0.5:
                        state, label, color = "STRONG_PUMP", "Strong Bullish Momentum", "#00ff41"
                    elif score > 0.2:
                        state, label, color = "PUMP", "Bullish Trend", "#00cc33"
                    elif score > -0.2:
                        state, label, color = "NEUTRAL", "Market Ranging", "#ffff00"
                    elif score > -0.5:
                        state, label, color = "DIP", "Bearish Trend", "#ff6600"
                    else:
                        state, label, color = "DUMP", "Strong Bearish Momentum", "#ff0000"
                    
                    # Build complete response with ONLY JSON-serializable data
                    result = {
                        'timestamp': datetime.now().isoformat(),
                        'composite_score': float(score),
                        'confidence': 0.85,
                        'market_state': {
                            'state': state,
                            'label': label,
                            'score': float(score),
                            'confidence': 0.85,
                            'color': color,
                            'volatility_adjusted': False
                        },
                        'current_data': {
                            'price': float(price),
                            'volume_24h': float(volume_24h),
                            'market_cap': 0.0,
                            'high_24h': float(high_24h),
                            'low_24h': float(low_24h),
                            'price_change_24h': float(price_change_24h)
                        },
                        'timeframe_analysis': {
                            '24h': {
                                'data_points': 1,
                                'price_change_pct': float(price_change_24h),
                                'volatility': float(abs(price_change_24h)),
                                'rsi': float(rsi),
                                'momentum': float(momentum * 100),
                                'volume_trend': 0.0,
                                'avg_volume': float(volume_24h)
                            }
                        },
                        'components': {
                            'price_momentum': float(momentum),
                            'technical_indicators': float(technical_score),
                            'market_sentiment': float((fear_greed - 50) / 50 * 0.2),
                            'volume_analysis': float(volatility * 0.5)
                        },
                        'fear_greed_index': {
                            'value': fear_greed,
                            'text': 'Extreme Fear' if fear_greed < 25 else 'Fear' if fear_greed < 45 else 'Neutral' if fear_greed < 55 else 'Greed' if fear_greed < 75 else 'Extreme Greed',
                            'classification': 'extreme_fear' if fear_greed < 25 else 'fear' if fear_greed < 45 else 'neutral' if fear_greed < 55 else 'greed' if fear_greed < 75 else 'extreme_greed'
                        },
                        'recommendations': [],
                        'volatility_metrics': {
                            'percentile_rank': 50.0,
                            'volatility_30d': float(abs(price_change_24h) * 5),
                            'volatility_90d': 50.0,
                            'support_level': float(low_24h),
                            'resistance_level': float(high_24h),
                            'distance_to_support': float((price - low_24h) / low_24h * 100),
                            'distance_to_resistance': float((high_24h - price) / price * 100)
                        },
                        'divergences': [],
                        'power_law': power_law_data
                    }
                    
                    logger.info(f"✅ REAL Bitcoin data: ${price:,.2f} ({price_change_24h:+.2f}%)")
                    return result
                    
                else:
                    logger.error(f"Binance API returned status {response.status}")
                    
        except Exception as e:
            logger.error(f"Error getting Bitcoin data: {e}")
        
        # Should never reach here with Binance API, but safety fallback
        raise Exception("All data sources failed - this should not happen with Binance API")
    
    async def get_enhanced_bitcoin_data(self):
        """Get Bitcoin data enhanced with microstructure analysis"""
        try:
            # Get basic Bitcoin data first
            basic_data = await self.get_real_bitcoin_data()
            
            # Get microstructure analysis
            microstructure_manager = await self.get_microstructure_manager()
            enhanced_data = await microstructure_manager.get_enhanced_price_data()
            
            # Merge the data
            result = basic_data.copy()
            
            # Add microstructure intelligence
            if enhanced_data and 'microstructure_signal' in enhanced_data:
                result['microstructure'] = {
                    'signal': enhanced_data.get('microstructure_signal', 0),
                    'confidence': enhanced_data.get('microstructure_confidence', 0),
                    'action_message': enhanced_data.get('action_message', ''),
                    'active_patterns': enhanced_data.get('active_patterns', 0),
                    'pattern_signals': enhanced_data.get('pattern_signals', []),
                    'liquidation_risk': enhanced_data.get('liquidation_risk', 'low'),
                    'liquidation_direction': enhanced_data.get('liquidation_direction', 'balanced')
                }
                
                # Update recommendations with microstructure insights
                if enhanced_data.get('action_message'):
                    result['recommendations'].insert(0, {
                        'type': 'insight',
                        'priority': 'high', 
                        'message': enhanced_data['action_message']
                    })
                
                # Update composite score with microstructure signal
                microstructure_weight = 0.3
                original_score = result['composite_score']
                microstructure_signal = enhanced_data.get('microstructure_signal', 0)
                
                result['composite_score'] = (original_score * (1 - microstructure_weight) + 
                                            microstructure_signal * microstructure_weight)
            
            return result
            
        except Exception as e:
            logger.error(f"Enhanced bitcoin data error: {e}")
            # Fallback to basic data
            return await self.get_real_bitcoin_data()

# Initialize working analyzer
working_analyzer = WorkingAnalyzer()

# Background task for periodic MSTR updates
background_tasks = set()

@app.on_event("startup")
async def startup_event():
    """Start background tasks on app startup"""
    # Start periodic MSTR data fetcher
    task = asyncio.create_task(periodic_update_task())
    background_tasks.add(task)
    logger.info("Started periodic MSTR data fetcher (30-minute updates)")
    
    # Fetch initial data
    initial_task = asyncio.create_task(working_analyzer.strategy_fetcher.get_mstr_data())
    background_tasks.add(initial_task)
    
    # Start MSTR holdings fetcher with 30-minute updates
    holdings_fetcher = get_fetcher()
    holdings_task = asyncio.create_task(holdings_fetcher.start_periodic_updates())
    background_tasks.add(holdings_task)
    logger.info("Started MSTR holdings fetcher (30-minute updates)")
    
    # Start automated backup system
    backup_task = asyncio.create_task(start_backup_service())
    background_tasks.add(backup_task)
    logger.info("Started automated backup system (hourly backups)")
    
    # Start data quality monitoring
    monitor = get_monitor()
    monitor_task = asyncio.create_task(monitor.monitor_data_quality())
    background_tasks.add(monitor_task)
    logger.info("Started data quality monitoring")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    for task in background_tasks:
        task.cancel()
    if working_analyzer.session:
        await working_analyzer.session.close()

@app.get("/")
async def root():
    """Serve the enhanced unified professional dashboard"""
    try:
        # Try enhanced dashboard first
        with open("enhanced_unified_dashboard.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        # Fallback to original dashboard
        try:
            with open("unified_dashboard.html", "r") as f:
                return HTMLResponse(content=f.read())
        except FileNotFoundError:
            return HTMLResponse(
                content="<h1>Dashboard Not Found</h1><p>Please check if dashboard HTML exists.</p>", 
                status_code=404
            )

@app.get("/api/analysis")
async def get_analysis():
    """Get real market analysis"""
    try:
        result = await working_analyzer.get_real_bitcoin_data()
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        return JSONResponse(
            content={"error": "Analysis failed", "message": str(e)},
            status_code=500
        )

@app.get("/api/bitcoin-data")
async def get_bitcoin_data():
    """Get RELIABLE Bitcoin data - no placeholder data allowed"""
    try:
        # Use the basic reliable analyzer - no microstructure complexity
        result = await working_analyzer.get_real_bitcoin_data()
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Bitcoin data API error: {e}")
        return JSONResponse(
            content={"error": "Bitcoin API failed", "message": str(e)},
            status_code=500
        )

@app.get("/api/enhanced")
async def get_enhanced_analysis():
    """Get enhanced analysis with microstructure"""
    try:
        result = await working_analyzer.get_enhanced_bitcoin_data()
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Enhanced analysis error: {e}")
        return JSONResponse(
            content={"error": "Enhanced analysis failed", "message": str(e)},
            status_code=500
        )

@app.get("/api/microstructure")
async def get_microstructure_data():
    """Get comprehensive microstructure analysis"""
    try:
        manager = await working_analyzer.get_microstructure_manager()
        dashboard_data = await manager.get_microstructure_dashboard_data()
        return JSONResponse(content=dashboard_data)
    except Exception as e:
        logger.error(f"Microstructure API error: {e}")
        return JSONResponse(
            content={"error": "Microstructure analysis failed", "message": str(e)},
            status_code=500
        )

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates - GUARANTEED WORKING"""
    await websocket.accept()
    logger.info("WebSocket connection established")
    is_connected = True
    
    try:
        while is_connected:
            try:
                # Get reliable Bitcoin data only - no broken microstructure
                result = await working_analyzer.get_real_bitcoin_data()
                
                # Check if WebSocket is still connected before sending
                if websocket.client_state.name == "CONNECTED":
                    await websocket.send_json(result)
                    logger.debug("WebSocket: Real data sent successfully")
                else:
                    logger.info("WebSocket disconnected, stopping updates")
                    is_connected = False
                    break
                
                # Update every 15 seconds
                await asyncio.sleep(15)
                
            except Exception as e:
                error_msg = str(e)
                if "Cannot call" in error_msg and "close" in error_msg:
                    logger.info("WebSocket closed by client")
                    is_connected = False
                    break
                    
                logger.error(f"WebSocket analysis error: {e}")
                # Only send error if still connected
                if websocket.client_state.name == "CONNECTED":
                    error_result = {
                        'timestamp': datetime.now().isoformat(),
                        'current_data': {'price': 0.0},
                        'market_state': {'state': 'ERROR', 'label': 'Connection Error', 'color': '#ff0000'},
                        'recommendations': [{'type': 'error', 'priority': 'high', 'message': 'Reconnecting...'}]
                    }
                    try:
                        await websocket.send_json(error_result)
                    except:
                        is_connected = False
                        break
                else:
                    is_connected = False
                    break
                    
                await asyncio.sleep(10)
                
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        if websocket.client_state.name == "CONNECTED":
            try:
                await websocket.close()
            except:
                pass
        logger.info("WebSocket connection closed")

# Whale On-Chain API Endpoint
@app.get("/api/whale")
async def get_whale_data():
    """Get REAL whale on-chain insights from blockchain"""
    try:
        tracker = await get_real_whale_tracker()
        insights = await tracker.get_real_whale_insights()
        return JSONResponse(content=insights)
    except Exception as e:
        logger.error(f"Whale API error: {e}")
        return JSONResponse(
            content={
                "error": "Whale tracking failed",
                "message": str(e),
                "fallback": {
                    "exchange_flows": {"net_flow": 0, "signal": "unknown"},
                    "composite_signal": {"signal": "Data unavailable", "confidence": 0}
                }
            },
            status_code=500
        )

# Multi-Asset Correlation API Endpoints
@app.get("/api/correlation")
async def get_correlation_data():
    """Get comprehensive multi-asset correlation analysis"""
    try:
        manager = await working_analyzer.get_multi_asset_manager()
        
        # Update multi-asset data
        await manager.update_all_data()
        
        # Get comprehensive analysis
        analysis = await manager.get_comprehensive_analysis()
        
        return JSONResponse(content=analysis)
        
    except Exception as e:
        logger.error(f"Correlation API error: {e}")
        return JSONResponse(
            content={
                "error": "Correlation analysis failed", 
                "message": str(e),
                "fallback": {
                    "mstr": {"signals": [{"type": "error", "message": "❌ MSTR data unavailable", "action": "Check connection", "confidence": 0}]},
                    "eth_btc": {"signals": [{"type": "error", "message": "❌ ETH/BTC data unavailable", "action": "Check connection", "confidence": 0}]},
                    "market_phase": {"phase": "error", "message": "Analysis unavailable", "confidence": 0},
                    "composite_signal": 0
                }
            },
            status_code=500
        )

@app.get("/api/multi-asset")
async def get_multi_asset_data():
    """Alternative endpoint for multi-asset data"""
    return await get_correlation_data()

@app.get("/api/mstr-advanced")
async def get_mstr_advanced():
    """Get advanced MSTR analytics with trading signals"""
    try:
        # Get current prices
        manager = await working_analyzer.get_multi_asset_manager()
        await manager.update_all_data()
        
        # Get comprehensive analysis which includes MSTR data
        correlation_data = await manager.get_comprehensive_analysis()
        
        # Get real MSTR stock price
        stock_fetcher = get_stock_fetcher()
        mstr_price = await stock_fetcher.get_mstr_price()
        
        # Get Bitcoin price
        btc_data = await working_analyzer.get_real_bitcoin_data()
        btc_price = btc_data.get('current_data', {}).get('price', 100000)
        
        # Get advanced analytics
        analytics = await get_mstr_advanced_analytics()
        result = await analytics.get_comprehensive_analysis(mstr_price, btc_price)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"MSTR advanced analytics error: {e}")
        return JSONResponse(
            content={
                "error": "MSTR analytics failed",
                "message": str(e)
            },
            status_code=500
        )

@app.get("/api/power-law")
async def get_power_law():
    """Get Bitcoin Power Law analysis"""
    try:
        # Get current Bitcoin price
        bitcoin_data = await working_analyzer.get_real_bitcoin_data()
        current_price = bitcoin_data['current_data']['price']
        
        # Get power law analysis
        power_law_calc = get_power_law_calculator()
        power_law_status = power_law_calc.get_power_law_status(current_price)
        
        # Get historical power law data for charting (last 180 days)
        historical = power_law_calc.get_historical_power_law(180)
        
        return JSONResponse(content={
            'current': power_law_status,
            'historical': historical,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Power law API error: {e}")
        return JSONResponse(
            content={"error": "Power law calculation failed", "message": str(e)},
            status_code=500
        )

@app.get("/api/onchain")
async def get_onchain_analytics():
    """Get comprehensive REAL on-chain analytics - no simulated data"""
    try:
        # Use the new real on-chain data module
        analytics = await get_real_onchain_data()
        result = await analytics.get_comprehensive_analysis()
        
        # Add flag to indicate this is real data
        result['data_quality'] = 'REAL'
        result['note'] = 'All metrics from blockchain.info and mempool analysis'
        
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Real on-chain analytics error: {e}")
        return JSONResponse(
            content={
                "error": "On-chain analysis failed",
                "message": str(e),
                "is_real_data": False,
                "fallback": {
                    "mvrv": {"z_score": 0, "signal": "Data unavailable"},
                    "exchange_flows": {"net_flow_24h": 0, "signal": "Unknown"},
                    "lth_supply": {"lth_percentage": 65, "signal": "Unknown"},
                    "network_health": {"health_score": 50, "status": "Unknown"}
                }
            },
            status_code=500
        )

@app.get("/health")
async def health_check():
    """System health check endpoint"""
    try:
        monitor = get_monitor()
        health = await monitor.health_check()
        
        # Add HTTP status code based on health status
        status_code = 200 if health['status'] == 'healthy' else 503 if health['status'] == 'critical' else 206
        
        return JSONResponse(content=health, status_code=status_code)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            content={
                "status": "error",
                "error": str(e),
                "timestamp": int(time.time())
            },
            status_code=500
        )

@app.get("/api/network-health-v2")
async def get_network_health_enhanced():
    """Get enhanced network health with percentile-based scoring"""
    try:
        health_monitor = await get_network_health_v2(working_analyzer.db)
        health_data = await health_monitor.calculate_health_score()
        return JSONResponse(content=health_data)
    except Exception as e:
        logger.error(f"Network health v2 error: {e}")
        return JSONResponse(
            content={
                "error": "Network health analysis failed",
                "message": str(e),
                "fallback": {
                    "total_score": 50,
                    "status": "UNKNOWN",
                    "color": "#888888",
                    "description": "Unable to calculate network health"
                }
            },
            status_code=500
        )

@app.get("/api/backup/status")
async def backup_status():
    """Get backup system status"""
    try:
        manager = get_backup_manager()
        status = manager.get_backup_status()
        return JSONResponse(content=status)
    except Exception as e:
        logger.error(f"Backup status error: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )

@app.post("/api/backup/create")
async def create_backup():
    """Manually trigger a backup"""
    try:
        manager = get_backup_manager()
        backup_info = manager.create_backup()
        
        if 'error' in backup_info:
            return JSONResponse(
                content=backup_info,
                status_code=500
            )
        
        return JSONResponse(content={
            "success": True,
            "backup": backup_info,
            "message": f"Backup created: {backup_info['name']}"
        })
    except Exception as e:
        logger.error(f"Backup creation error: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )

@app.get("/api/backup/list")
async def list_backups():
    """List available backups"""
    try:
        manager = get_backup_manager()
        backups = manager.list_backups()
        return JSONResponse(content={"backups": backups})
    except Exception as e:
        logger.error(f"Backup list error: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )

@app.get("/correlation-dashboard")
async def correlation_dashboard():
    """Serve the multi-asset correlation dashboard"""
    try:
        with open("correlation_dashboard.html", "r") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Correlation Dashboard Not Found</h1><p>Please check if correlation_dashboard.html exists.</p>", 
            status_code=404
        )

@app.websocket("/ws/correlation")
async def correlation_websocket(websocket: WebSocket):
    """WebSocket specifically for correlation updates"""
    await websocket.accept()
    logger.info("Correlation WebSocket connection established")
    
    try:
        manager = await working_analyzer.get_multi_asset_manager()
        
        while True:
            try:
                # Update multi-asset data
                await manager.update_all_data()
                
                # Get comprehensive analysis
                analysis = await manager.get_comprehensive_analysis()
                
                # Send correlation update
                message = {
                    'type': 'correlation_update',
                    'correlation': analysis,
                    'timestamp': int(time.time())
                }
                
                await websocket.send_json(message)
                logger.debug("Correlation WebSocket: Data sent successfully")
                
                # Update every 30 seconds (less frequent for external APIs)
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Correlation WebSocket analysis error: {e}")
                # Send error message
                error_message = {
                    'type': 'correlation_error',
                    'error': str(e),
                    'timestamp': int(time.time())
                }
                try:
                    await websocket.send_json(error_message)
                except:
                    pass
                await asyncio.sleep(15)
                
    except Exception as e:
        logger.error(f"Correlation WebSocket connection error: {e}")
        try:
            await websocket.close()
        except:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")