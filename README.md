# Bitcoin & Multi-Asset Professional Analyzer

A comprehensive real-time Bitcoin market analyzer with on-chain intelligence, multi-asset correlation tracking, and professional-grade market microstructure analysis.

## Features

### Core Analytics
- **Real-Time Price Tracking**: Live Bitcoin price updates from multiple exchanges
- **Power Law Model**: Fair value calculation based on Bitcoin's historical growth trajectory
- **Fear & Greed Index**: Market sentiment analysis with 7 components
- **Technical Indicators**: RSI, MACD, Bollinger Bands, and custom momentum indicators

### On-Chain Intelligence (100% Real Data)
- **MVRV Z-Score**: Market Value to Realized Value ratio for identifying market tops/bottoms
- **Exchange Flows**: Real-time tracking of Bitcoin flows to/from major exchanges
- **Long-Term Holder Supply**: Analysis of HODLer behavior and conviction
- **Network Health Metrics**: Hash rate, transaction volume, and network security scoring

### Multi-Asset Correlation
- **MSTR Premium Tracking**: MicroStrategy NAV premium/discount analysis
- **ETH/BTC Ratio**: Ethereum strength relative to Bitcoin
- **SOL/BTC Ratio**: Solana momentum and market rotation signals
- **Market Phase Detection**: Automated identification of risk-on/risk-off cycles

### Professional Features
- **Market Microstructure Analysis**: Order book depth, bid-ask spreads, liquidation cascades
- **Pattern Recognition**: Wyckoff accumulation/distribution, stop hunting detection
- **Backtesting Framework**: Strategy testing with historical data
- **WebSocket Real-Time Updates**: Live data streaming for all metrics

## Quick Start

### Installation

```bash
# Clone the repository
git clone git@github.com:StevenGeller/btc-analyzer.git
cd btc-analyzer

# Install dependencies
pip install -r requirements.txt
```

### Running the Application

```bash
# Professional version with all features
python professional_app.py

# Standard version
python working_app.py

# Simple version for testing
python simple_app.py
```

The application will be available at `http://localhost:8000`

## API Endpoints

- `/` - Enhanced unified dashboard
- `/api/analysis` - Comprehensive market analysis
- `/api/onchain` - On-chain analytics (MVRV, exchange flows, LTH supply)
- `/api/power-law` - Bitcoin Power Law model calculations
- `/api/correlation` - Multi-asset correlation data
- `/api/microstructure` - Market microstructure metrics
- `/api/patterns` - Pattern recognition results
- `/ws` - WebSocket for real-time updates

## Data Sources

All data is fetched from legitimate, free APIs without requiring API keys:

- **Price Data**: Binance, Coinbase, CoinGecko
- **On-Chain Data**: Blockchain.info, Mempool.space
- **Sentiment**: Alternative.me Fear & Greed Index
- **Multi-Asset**: Yahoo Finance (MSTR), CoinGecko (ETH, SOL)

## Architecture

```
External APIs → DataFetcher → SQLite Database → Analyzer → FastAPI → WebSocket/HTTP → Dashboard
     ↓              ↓              ↓               ↓          ↓
Rate Limiting → Caching → WAL Mode Storage → Analysis → Real-time Updates
```

### Key Components

- `database.py` - SQLite with WAL mode for concurrent access
- `optimized_data_fetcher.py` - Multi-source data aggregation
- `enhanced_analyzer.py` - Composite scoring and market state detection
- `real_onchain_data.py` - 100% real blockchain data (no simulations)
- `power_law_calculator.py` - Bitcoin fair value model
- `microstructure_integration.py` - Professional market depth analysis
- `pattern_recognition.py` - Advanced pattern detection algorithms

## Configuration

The system is designed to work out-of-the-box without configuration. However, you can customize:

- **Update Intervals**: Modify polling rates in data fetchers
- **Database Retention**: Adjust the 30-day cleanup window
- **WebSocket Settings**: Configure reconnection intervals
- **Display Preferences**: Customize dashboard layout and colors

## Development

### Testing

```bash
# Test data fetcher
python test_fetcher.py

# Test on-chain endpoints
python test_onchain_endpoints.py

# Test robust system
python test_robust_system.py
```

### Database Management

The SQLite database uses WAL mode for optimal performance:
- Automatic cleanup of data older than 30 days
- Optimized indexes for time-series queries
- Concurrent read/write support

## Key Features Explained

### Power Law Model
Calculates Bitcoin's "fair value" based on time since genesis block (Jan 3, 2009):
- Fair Value = 10^(-17.01) × (days since genesis)^5.82
- Resistance = Fair Value × 3.2
- Support = Fair Value × 0.35

### MVRV Z-Score
- Compares market cap to realized cap
- Z-Score < 0: Undervalued (Buy signal)
- Z-Score > 3: Overvalued (Sell signal)

### Exchange Flow Analysis
Tracks Bitcoin movement to/from known exchange wallets:
- Inflow > 100 BTC/day: Bearish (selling pressure)
- Outflow > 100 BTC/day: Bullish (accumulation)

## Performance

- **Update Frequency**: 5-second intervals for price data
- **On-Chain Refresh**: 5-minute cache for blockchain data
- **Database Optimization**: WAL mode with optimized PRAGMA settings
- **Memory Usage**: ~100-200MB typical
- **CPU Usage**: <5% on modern systems

## Contributing

This project prioritizes real data integrity and professional-grade analysis. Contributions should:
1. Never introduce mock or simulated data
2. Follow existing code patterns and conventions
3. Include proper error handling and logging
4. Add tests for new features

## License

MIT License - See LICENSE file for details

## Author

Steven Geller

## Acknowledgments

Built with real-time data from public blockchain APIs and exchange feeds. Special thanks to the Bitcoin community for maintaining open data standards.

---

**Note**: This system is for educational and research purposes. Always do your own research before making investment decisions.