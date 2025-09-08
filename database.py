import sqlite3
import json
import time
from datetime import datetime, timedelta
from contextlib import contextmanager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path='bitcoin_analyzer.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite with optimized settings for real-time data"""
        with self.get_connection() as conn:
            # Performance optimizations
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            conn.execute("PRAGMA temp_store=MEMORY")
            
            # Main price table with all real data fields
            conn.execute("""
                CREATE TABLE IF NOT EXISTS price_data (
                    timestamp INTEGER PRIMARY KEY,
                    price REAL NOT NULL,
                    volume_24h REAL,
                    volume_1h REAL,
                    high_24h REAL,
                    low_24h REAL,
                    price_change_1h REAL,
                    price_change_24h REAL,
                    price_change_7d REAL,
                    market_cap REAL,
                    total_volume REAL,
                    bid REAL,
                    ask REAL,
                    spread REAL
                )
            """)
            
            # Technical indicators table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS indicators (
                    timestamp INTEGER PRIMARY KEY,
                    rsi_14 REAL,
                    macd REAL,
                    macd_signal REAL,
                    bb_upper REAL,
                    bb_middle REAL,
                    bb_lower REAL,
                    ema_20 REAL,
                    ema_50 REAL,
                    ema_200 REAL,
                    volume_sma REAL,
                    atr_14 REAL,
                    stoch_k REAL,
                    stoch_d REAL
                )
            """)
            
            # Enhanced market metrics table - REAL DATA ONLY
            conn.execute("""
                CREATE TABLE IF NOT EXISTS market_metrics (
                    timestamp INTEGER PRIMARY KEY,
                    fear_greed_index INTEGER,
                    fear_greed_class TEXT,
                    long_short_ratio REAL,
                    top_trader_ratio REAL,
                    funding_rate REAL,
                    open_interest REAL,
                    liquidations_24h REAL,
                    exchange_netflow REAL,
                    active_addresses INTEGER,
                    hash_rate REAL,
                    order_book_imbalance REAL,
                    bid_volume REAL,
                    ask_volume REAL,
                    btc_dominance REAL,
                    total_market_cap REAL,
                    altcoin_market_cap REAL,
                    source TEXT DEFAULT 'unknown'
                )
            """)
            
            # Exchange comparison table for arbitrage detection
            conn.execute("""
                CREATE TABLE IF NOT EXISTS exchange_prices (
                    timestamp INTEGER,
                    exchange TEXT,
                    price REAL NOT NULL,
                    volume REAL,
                    bid REAL,
                    ask REAL,
                    source TEXT DEFAULT 'api',
                    PRIMARY KEY (timestamp, exchange)
                )
            """)
            
            # MSTR price history for beta calculations
            conn.execute("""
                CREATE TABLE IF NOT EXISTS mstr_prices (
                    timestamp INTEGER PRIMARY KEY,
                    price REAL NOT NULL,
                    volume REAL,
                    market_cap REAL,
                    nav_premium REAL,
                    source TEXT DEFAULT 'yahoo'
                )
            """)
            
            # Network metrics table for percentile-based health scoring
            conn.execute("""
                CREATE TABLE IF NOT EXISTS network_metrics (
                    timestamp INTEGER PRIMARY KEY,
                    hash_rate REAL,
                    hash_rate_eh REAL,  -- In ExaHash/s for easier reading
                    difficulty REAL,
                    daily_transactions INTEGER,
                    mempool_size INTEGER,
                    minutes_between_blocks REAL,
                    total_fees_btc REAL,
                    node_count INTEGER,
                    lightning_capacity_btc REAL,
                    lightning_channels INTEGER,
                    mining_herfindahl_index REAL,
                    top_4_pool_concentration REAL,
                    largest_pool_share REAL,
                    block_height INTEGER,
                    average_block_size INTEGER,
                    median_fee_sat_byte REAL,
                    data_source TEXT DEFAULT 'mixed'
                )
            """)
            
            # Real-time trade data for granular analysis
            conn.execute("""
                CREATE TABLE IF NOT EXISTS realtime_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    price REAL NOT NULL,
                    quantity REAL NOT NULL,
                    is_buyer_maker BOOLEAN,
                    trade_time INTEGER,
                    exchange TEXT DEFAULT 'binance'
                )
            """)
            
            # Data quality and source tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS data_quality (
                    timestamp INTEGER PRIMARY KEY,
                    sources_active INTEGER,
                    primary_source TEXT,
                    backup_sources TEXT,
                    data_freshness INTEGER,
                    validation_passed BOOLEAN,
                    arbitrage_opportunities INTEGER,
                    api_calls_made INTEGER,
                    errors_encountered INTEGER
                )
            """)
            
            # Analysis cache
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analysis_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    timeframe TEXT NOT NULL,
                    composite_score REAL,
                    confidence REAL,
                    market_state TEXT,
                    analysis_json TEXT,
                    created_at INTEGER DEFAULT (strftime('%s', 'now'))
                )
            """)
            
            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_price_timestamp ON price_data(timestamp DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_indicators_timestamp ON indicators(timestamp DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON market_metrics(timestamp DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_analysis_timestamp ON analysis_results(timestamp DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_exchange_timestamp ON exchange_prices(timestamp DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON realtime_trades(timestamp DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_quality_timestamp ON data_quality(timestamp DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_exchange_name ON exchange_prices(exchange)")
            
            # Add columns to existing tables if they don't exist (migration support)
            try:
                conn.execute("ALTER TABLE market_metrics ADD COLUMN fear_greed_class TEXT")
                conn.execute("ALTER TABLE market_metrics ADD COLUMN top_trader_ratio REAL")
                conn.execute("ALTER TABLE market_metrics ADD COLUMN order_book_imbalance REAL")
                conn.execute("ALTER TABLE market_metrics ADD COLUMN bid_volume REAL")
                conn.execute("ALTER TABLE market_metrics ADD COLUMN ask_volume REAL")
                conn.execute("ALTER TABLE market_metrics ADD COLUMN btc_dominance REAL")
                conn.execute("ALTER TABLE market_metrics ADD COLUMN total_market_cap REAL")
                conn.execute("ALTER TABLE market_metrics ADD COLUMN altcoin_market_cap REAL")
                conn.execute("ALTER TABLE market_metrics ADD COLUMN source TEXT DEFAULT 'unknown'")
            except sqlite3.OperationalError:
                pass  # Columns already exist
            
            # Order flow and microstructure tables
            conn.execute('''
                CREATE TABLE IF NOT EXISTS order_flow_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    delta REAL NOT NULL,
                    cumulative_delta REAL NOT NULL,
                    buy_volume REAL NOT NULL,
                    sell_volume REAL NOT NULL,
                    aggression_score REAL,
                    whale_bias REAL,
                    trade_count INTEGER,
                    whale_trades INTEGER,
                    source TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS liquidation_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    exchange TEXT NOT NULL,
                    long_liquidations_usd REAL DEFAULT 0,
                    short_liquidations_usd REAL DEFAULT 0,
                    total_usd REAL NOT NULL,
                    price REAL,
                    quantity REAL,
                    side TEXT,
                    source TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS funding_rates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    exchange TEXT NOT NULL,
                    funding_rate REAL NOT NULL,
                    open_interest REAL,
                    next_funding_time INTEGER,
                    source TEXT DEFAULT 'api'
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS tight_spreads (
                    timestamp INTEGER PRIMARY KEY,
                    bid REAL NOT NULL,
                    ask REAL NOT NULL,
                    spread_bps REAL NOT NULL
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS whale_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    price REAL NOT NULL,
                    quantity REAL NOT NULL,
                    value_usd REAL NOT NULL,
                    is_market_buy BOOLEAN NOT NULL,
                    trade_size_category TEXT,
                    trade_id TEXT,
                    source TEXT,
                    UNIQUE(trade_id, timestamp) ON CONFLICT IGNORE
                )
            ''')
            
            # Create index for faster whale trade queries
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_whale_trades_timestamp 
                ON whale_trades(timestamp DESC)
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS pattern_detections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    pattern_type TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    price_level REAL,
                    direction TEXT,
                    message TEXT,
                    action TEXT,
                    data_json TEXT
                )
            ''')
            
            # Create indexes for new tables
            conn.execute("CREATE INDEX IF NOT EXISTS idx_order_flow_timestamp ON order_flow_data(timestamp DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_liquidations_timestamp ON liquidation_events(timestamp DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_funding_timestamp ON funding_rates(timestamp DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_whale_trades_timestamp ON whale_trades(timestamp DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_patterns_timestamp ON pattern_detections(timestamp DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_liquidations_exchange ON liquidation_events(exchange)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_funding_exchange ON funding_rates(exchange)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_patterns_type ON pattern_detections(pattern_type)")
            
            logger.info("Database initialized successfully with microstructure tables")
    
    @contextmanager
    def get_connection(self):
        """Thread-safe connection context manager"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def get_latest_price_data(self, hours=24):
        """Get recent price data"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM price_data 
                WHERE timestamp > ? 
                ORDER BY timestamp DESC
            """, (int((datetime.now() - timedelta(hours=hours)).timestamp()),))
            return cursor.fetchall()
    
    def cleanup_old_data(self, days=30):
        """Remove data older than specified days"""
        cutoff = int((datetime.now() - timedelta(days=days)).timestamp())
        with self.get_connection() as conn:
            conn.execute("DELETE FROM price_data WHERE timestamp < ?", (cutoff,))
            conn.execute("DELETE FROM indicators WHERE timestamp < ?", (cutoff,))
            conn.execute("DELETE FROM market_metrics WHERE timestamp < ?", (cutoff,))
            conn.execute("DELETE FROM exchange_prices WHERE timestamp < ?", (cutoff,))
            conn.execute("DELETE FROM realtime_trades WHERE timestamp < ?", (cutoff,))
            conn.execute("DELETE FROM data_quality WHERE timestamp < ?", (cutoff,))
            logger.info(f"Cleaned up data older than {days} days")
    
    def get_exchange_prices(self, minutes=60):
        """Get recent exchange prices for arbitrage analysis"""
        cutoff = int((datetime.now() - timedelta(minutes=minutes)).timestamp())
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM exchange_prices 
                WHERE timestamp > ? 
                ORDER BY timestamp DESC, exchange
            """, (cutoff,))
            return cursor.fetchall()
    
    def get_data_quality_status(self):
        """Get latest data quality metrics"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM data_quality 
                ORDER BY timestamp DESC 
                LIMIT 1
            """)
            return cursor.fetchone()
    
    def store_real_price_data(self, price_data: dict):
        """Store validated real price data"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO price_data 
                (timestamp, price, volume_24h, volume_1h, high_24h, low_24h,
                 price_change_1h, price_change_24h, price_change_7d, 
                 market_cap, total_volume, bid, ask, spread)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                price_data.get('timestamp', int(time.time())),
                price_data['price'],
                price_data.get('volume_24h', 0),
                price_data.get('volume_1h', 0),
                price_data.get('high_24h', price_data['price']),
                price_data.get('low_24h', price_data['price']),
                price_data.get('price_change_1h', 0),
                price_data.get('price_change_24h', 0),
                price_data.get('price_change_7d', 0),
                price_data.get('market_cap', 0),
                price_data.get('total_volume', 0),
                price_data.get('bid', price_data['price'] - 1),
                price_data.get('ask', price_data['price'] + 1),
                price_data.get('spread', 2)
            ))
    
    def store_exchange_price(self, exchange: str, price_data: dict):
        """Store price from specific exchange"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO exchange_prices
                (timestamp, exchange, price, volume, bid, ask, source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                price_data.get('timestamp', int(time.time())),
                exchange,
                price_data['price'],
                price_data.get('volume', 0),
                price_data.get('bid', price_data['price'] - 1),
                price_data.get('ask', price_data['price'] + 1),
                price_data.get('source', 'api')
            ))
    
    def store_market_metrics(self, metrics_data: dict):
        """Store real market metrics data"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO market_metrics
                (timestamp, fear_greed_index, fear_greed_class, long_short_ratio,
                 top_trader_ratio, funding_rate, open_interest, order_book_imbalance,
                 bid_volume, ask_volume, btc_dominance, total_market_cap, 
                 altcoin_market_cap, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metrics_data.get('timestamp', int(time.time())),
                metrics_data.get('fear_greed_index'),
                metrics_data.get('fear_greed_class'),
                metrics_data.get('long_short_ratio'),
                metrics_data.get('top_trader_ratio'),
                metrics_data.get('funding_rate'),
                metrics_data.get('open_interest'),
                metrics_data.get('order_book_imbalance'),
                metrics_data.get('bid_volume'),
                metrics_data.get('ask_volume'),
                metrics_data.get('btc_dominance'),
                metrics_data.get('total_market_cap'),
                metrics_data.get('altcoin_market_cap'),
                metrics_data.get('source', 'unknown')
            ))
    
    def store_data_quality(self, quality_data: dict):
        """Store data quality metrics"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO data_quality
                (timestamp, sources_active, primary_source, backup_sources,
                 data_freshness, validation_passed, arbitrage_opportunities,
                 api_calls_made, errors_encountered)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                quality_data.get('timestamp', int(time.time())),
                quality_data.get('sources_active', 0),
                quality_data.get('primary_source', 'unknown'),
                quality_data.get('backup_sources', ''),
                quality_data.get('data_freshness', 0),
                quality_data.get('validation_passed', False),
                quality_data.get('arbitrage_opportunities', 0),
                quality_data.get('api_calls_made', 0),
                quality_data.get('errors_encountered', 0)
            ))
    
    def get_latest_real_price(self) -> dict:
        """Get the latest REAL Bitcoin price - never returns mock data"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM price_data 
                WHERE price > 10000 AND price < 1000000
                ORDER BY timestamp DESC 
                LIMIT 1
            """)
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            else:
                raise ValueError("No valid Bitcoin price data available")
    
    def validate_data_integrity(self):
        """Validate that all stored data is real, not mock"""
        issues = []
        
        with self.get_connection() as conn:
            # Check for invalid Bitcoin prices
            cursor = conn.execute("""
                SELECT COUNT(*) as count FROM price_data 
                WHERE price <= 10000 OR price >= 1000000
            """)
            invalid_prices = cursor.fetchone()['count']
            if invalid_prices > 0:
                issues.append(f"{invalid_prices} invalid Bitcoin prices found")
            
            # Check for missing timestamps
            cursor = conn.execute("""
                SELECT COUNT(*) as count FROM price_data 
                WHERE timestamp IS NULL OR timestamp = 0
            """)
            missing_timestamps = cursor.fetchone()['count']
            if missing_timestamps > 0:
                issues.append(f"{missing_timestamps} records with missing timestamps")
            
            # Check data freshness
            cutoff = int((datetime.now() - timedelta(minutes=10)).timestamp())
            cursor = conn.execute("""
                SELECT MAX(timestamp) as latest FROM price_data
            """)
            latest = cursor.fetchone()['latest']
            if latest and latest < cutoff:
                issues.append(f"Data is stale - latest update {(int(time.time()) - latest)//60} minutes ago")
        
        return issues
    
    def store_order_flow_data(self, order_flow_data: dict):
        """Store order flow analysis data"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO order_flow_data
                (timestamp, delta, cumulative_delta, buy_volume, sell_volume,
                 aggression_score, whale_bias, trade_count, whale_trades, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_flow_data.get('timestamp', int(time.time())),
                order_flow_data['delta'],
                order_flow_data['cumulative_delta'],
                order_flow_data['buy_volume'],
                order_flow_data['sell_volume'],
                order_flow_data.get('aggression_score'),
                order_flow_data.get('whale_bias'),
                order_flow_data.get('total_trades'),
                order_flow_data.get('whale_trades_count'),
                order_flow_data.get('source', 'websocket')
            ))
    
    def store_whale_trade(self, whale_trade: dict):
        """Store individual whale trade with deduplication"""
        with self.get_connection() as conn:
            # Use INSERT OR IGNORE to prevent duplicates based on trade_id and timestamp
            conn.execute("""
                INSERT OR IGNORE INTO whale_trades
                (timestamp, price, quantity, value_usd, is_market_buy,
                 trade_size_category, trade_id, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                whale_trade['timestamp'],
                whale_trade['price'],
                whale_trade['quantity'],
                whale_trade['value_usd'],
                whale_trade['is_market_buy'],
                whale_trade.get('trade_size_category', 'whale'),
                whale_trade.get('trade_id'),
                whale_trade.get('source', 'websocket')
            ))
    
    def store_pattern_detection(self, pattern: dict):
        """Store pattern detection result"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO pattern_detections
                (timestamp, pattern_type, confidence, price_level, direction,
                 message, action, data_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pattern.get('timestamp', int(time.time())),
                pattern['pattern_type'],
                pattern['confidence'],
                pattern.get('price_level'),
                pattern.get('direction'),
                pattern.get('message'),
                pattern.get('action'),
                json.dumps(pattern.get('data', {}))
            ))
    
    def get_order_flow_history(self, hours: int = 1) -> list:
        """Get order flow data for analysis"""
        cutoff = int((datetime.now() - timedelta(hours=hours)).timestamp())
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM order_flow_data 
                WHERE timestamp > ? 
                ORDER BY timestamp ASC
            """, (cutoff,))
            return cursor.fetchall()
    
    def get_recent_patterns(self, hours: int = 24) -> list:
        """Get recent pattern detections"""
        cutoff = int((datetime.now() - timedelta(hours=hours)).timestamp())
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM pattern_detections 
                WHERE timestamp > ? 
                ORDER BY timestamp DESC, confidence DESC
            """, (cutoff,))
            return cursor.fetchall()
    
    def get_liquidation_summary(self, hours: int = 1) -> dict:
        """Get liquidation summary for risk assessment"""
        cutoff = int((datetime.now() - timedelta(hours=hours)).timestamp())
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    SUM(long_liquidations_usd) as total_longs,
                    SUM(short_liquidations_usd) as total_shorts,
                    SUM(total_usd) as total_liquidations,
                    COUNT(*) as event_count,
                    MAX(total_usd) as largest_single
                FROM liquidation_events
                WHERE timestamp > ?
            """, (cutoff,))
            result = cursor.fetchone()
            return dict(result) if result else {}
    
    def cleanup_old_microstructure_data(self, days=7):
        """Clean up old microstructure data (keep shorter retention)"""
        cutoff = int((datetime.now() - timedelta(days=days)).timestamp())
        with self.get_connection() as conn:
            conn.execute("DELETE FROM order_flow_data WHERE timestamp < ?", (cutoff,))
            conn.execute("DELETE FROM whale_trades WHERE timestamp < ?", (cutoff,))
            conn.execute("DELETE FROM tight_spreads WHERE timestamp < ?", (cutoff,))
            # Keep liquidations and patterns longer
            pattern_cutoff = int((datetime.now() - timedelta(days=30)).timestamp())
            conn.execute("DELETE FROM liquidation_events WHERE timestamp < ?", (pattern_cutoff,))
            conn.execute("DELETE FROM pattern_detections WHERE timestamp < ?", (pattern_cutoff,))
            logger.info(f"Cleaned up microstructure data older than {days} days")