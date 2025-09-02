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

# Dashboard testing
python test_dashboard.py
```

### Application Access
The FastAPI application runs on `http://0.0.0.0:8000` by default with the unified dashboard at the root URL.

## Code Architecture

### Core Components

**Database Layer** (`database.py`)
- SQLite database with WAL mode for concurrent access
- 15+ optimized tables for financial data storage
- Tables: `price_data`, `indicators`, `market_metrics`, `whale_trades`, `liquidation_events`, `funding_rates`
- Automated 30-day data cleanup and integrity validation

**Data Fetching** (`strategy_fetcher.py`, `real_whale_tracker.py`)
- Multi-source API integration (Binance, CoinGecko, Alternative.me, Blockchain.info, Mempool.space)
- Asynchronous data collection with rate limiting
- Real-time WebSocket streaming capabilities
- Aggressive fallback chains across multiple sources

**Market Analysis** (`multi_asset_analyzer.py`, `pattern_recognition.py`, `microstructure_integration.py`)
- Composite scoring system combining price action, momentum, sentiment, and volume
- Technical indicators (RSI, MACD, Bollinger Bands)
- Wyckoff pattern detection and divergence analysis
- MSTR/BTC correlation with NAV premium tracking
- Order flow analysis with whale bias detection

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
- `/health` - System health monitoring

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

## Application Structure

### Main Application
- `working_app.py` - Production FastAPI application serving unified dashboard
- Integrates all system components: multi-asset analysis, microstructure, whale tracking
- CORS enabled for frontend integration

### Archived Variants (in `/archive/`)
- `app.py` - Basic market analysis
- `professional_app.py` - Full-featured with advanced analysis
- `simple_app.py` - Lightweight price tracking

### Key Modules
- `database.py` - Database operations and schema management
- `config.py` - Centralized configuration and constants
- `strategy_fetcher.py` - MSTR data fetching with caching
- `multi_asset_analyzer.py` - Cross-asset correlation analysis
- `real_whale_tracker.py` - On-chain whale movement tracking
- `pattern_recognition.py` - Technical pattern detection
- `microstructure_integration.py` - Market microstructure analysis

### Frontend Dashboards
- `unified_dashboard.html` - Main professional interface
- `correlation_dashboard.html` - Multi-asset correlation view
- `microstructure_dashboard.html` - Advanced order flow analysis

## Development Notes

- The codebase prioritizes real market data integrity over all other concerns
- WebSocket integration provides real-time updates to frontend dashboards
- Professional features include institutional-quality market microstructure analysis
- All APIs are integrated without requiring API keys for basic functionality
- Background tasks are properly managed with cleanup handlers
- System includes comprehensive monitoring and health checks