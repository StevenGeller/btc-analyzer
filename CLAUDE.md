# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
```bash
# Install dependencies
pip install -r requirements.txt

# Main production application (recommended)
python working_app.py

# System testing
python final_test.py
python verify_data.py
python test_dashboard.py
python test_onchain_endpoints.py

# Dashboard testing with specific modules  
python test_final_display.py
python test_all_dashboard_sections.py
python test_network_insights.py
```

### Application Access
The FastAPI application runs on `http://0.0.0.0:8000` by default with the unified dashboard at the root URL.

## Code Architecture

### Core Components

**Database Layer** (`database.py`)
- SQLite database with WAL mode for concurrent access
- 15+ optimized tables for financial data storage
- Tables: `price_data`, `indicators`, `market_metrics`, `whale_trades`, `liquidation_events`, `funding_rates`, `exchange_prices`
- Automated 30-day data cleanup and integrity validation
- PRAGMA optimizations: WAL journal mode, NORMAL synchronous, 10000 cache size

**Configuration** (`config.py`)
- Centralized configuration for all API endpoints and rate limits
- Cache duration settings for different data types
- Validation rules for price ranges and data integrity
- Exchange addresses for whale tracking

**Data Fetching** 
- `strategy_fetcher.py` - MSTR data fetcher with 30-minute periodic updates
- `real_whale_tracker.py` - On-chain whale transaction monitoring
- `real_onchain_data.py` - Blockchain.info and Mempool.space integration
- Multi-source API integration with aggressive fallback chains
- Real-time WebSocket streaming capabilities

**Market Analysis**
- `multi_asset_analyzer.py` - Cross-asset correlation (MSTR, ETH, SOL)
- `pattern_recognition.py` - Wyckoff patterns and divergence detection
- `microstructure_integration.py` - Order flow and market depth analysis
- `power_law_calculator.py` - Bitcoin fair value model calculations
- Composite scoring system combining multiple market factors

**System Infrastructure**
- `monitoring.py` - Health checks and data quality monitoring
- `backup_manager.py` - Automated hourly database backups
- `cache_manager.py` - Intelligent caching with TTL management
- `data_validator.py` - Data validation and integrity checks

### Data Flow Architecture

```
External APIs → Data Fetchers → SQLite Database → Analyzers → FastAPI Endpoints → WebSocket/HTTP Clients
     ↓              ↓              ↓                ↓                ↓
Rate Limiting → Validation → WAL Storage → Analysis → Real-time Updates
```

### API Endpoints

**WebSocket Endpoints**
- `/ws` - Real-time market updates (15-second intervals)
- `/ws/correlation` - Multi-asset correlation streams (30-second intervals)

**REST Endpoints**
- `/api/analysis` - Market analysis with composite scoring
- `/api/bitcoin-data` - Core Bitcoin price data
- `/api/enhanced` - Analysis with microstructure insights
- `/api/whale` - On-chain whale tracking
- `/api/correlation` - Multi-asset correlation data
- `/api/power-law` - Bitcoin Power Law analysis
- `/api/onchain` - Comprehensive on-chain analytics
- `/api/microstructure` - Market microstructure dashboard data
- `/api/backup/status` - Backup system status
- `/api/backup/create` - Manual backup trigger
- `/api/backup/list` - List available backups
- `/health` - System health monitoring

### Frontend Dashboards
- `enhanced_unified_dashboard.html` - Main professional interface (primary)
- `unified_dashboard.html` - Standard unified dashboard (fallback)
- `correlation_dashboard.html` - Multi-asset correlation view
- `microstructure_dashboard.html` - Advanced order flow analysis

## Critical Implementation Requirements

### Real Data Priority
This system **NEVER** returns mock or placeholder data:
- Always fetches real market data from working APIs
- Implements aggressive fallback chains across multiple data sources
- Caches real data and reuses when APIs are temporarily unavailable
- Shows clear error messages rather than fake data when all sources fail

### Data Validation
- Bitcoin price validation: must be between $10,000 - $1,000,000
- Timestamp validation: real-time data must be less than 5 minutes old
- Cross-validation between multiple API sources when possible
- Deduplication for whale trades and pattern detections

### Rate Limiting Strategy (from `config.py`)
- Binance: Unlimited (primary source)
- Alternative.me: Unlimited  
- CoinGecko: 30 calls/minute
- Blockchain.info: Conservative rate limiting
- Mempool.space: Conservative rate limiting

### Cache Durations
- MSTR data: 30 minutes
- Cryptocurrency data: 1 minute
- Whale data: 5 minutes
- Correlation data: 30 seconds

### Database Performance
- Uses SQLite with WAL mode for concurrent access
- Optimized PRAGMA settings for real-time data
- Strategic indexing on timestamp fields
- Automatic cleanup of data older than 30 days
- Transaction rollback on errors

## Background Services

The application starts several background services on startup:
- **MSTR Data Fetcher** - Updates every 30 minutes via `periodic_update_task()`
- **Automated Backup** - Hourly database backups via `start_backup_service()`
- **Data Quality Monitor** - Continuous monitoring via `monitor_data_quality()`

All background tasks are properly tracked in `background_tasks` set and cancelled on shutdown.

## Testing Strategy

Different test scripts verify specific functionality:
- `final_test.py` - Comprehensive system integration test
- `verify_data.py` - Data integrity and validation checks
- `test_dashboard.py` - Dashboard display and metrics verification
- `test_onchain_endpoints.py` - On-chain API endpoint testing
- `test_websocket.py` - WebSocket connection and streaming tests

## Development Notes

- The codebase prioritizes real market data integrity over all other concerns
- WebSocket integration provides real-time updates to frontend dashboards  
- Professional features include institutional-quality market microstructure analysis
- All APIs are integrated without requiring API keys for basic functionality
- Background tasks are properly managed with cleanup handlers
- System includes comprehensive monitoring and health checks
- Use of singleton patterns for managers (get_multi_asset_manager, get_microstructure_manager, etc.)