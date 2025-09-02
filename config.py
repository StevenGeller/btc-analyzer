"""
Unified Configuration File for BTC Analyzer
Best practices: All configuration in one place
"""
import os
from pathlib import Path

# Base Configuration
BASE_DIR = Path(__file__).parent
DATABASE_PATH = BASE_DIR / "bitcoin_analysis.db"
CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# API Configuration
API_CONFIG = {
    'binance': {
        'base_url': 'https://api.binance.com/api/v3',
        'ws_url': 'wss://stream.binance.com:9443/ws',
        'rate_limit': None,  # Unlimited
        'timeout': 10
    },
    'coingecko': {
        'base_url': 'https://api.coingecko.com/api/v3',
        'rate_limit': 30,  # calls per minute
        'timeout': 10
    },
    'blockchain_info': {
        'base_url': 'https://blockchain.info',
        'rate_limit': None,
        'timeout': 10
    },
    'mempool_space': {
        'base_url': 'https://mempool.space/api',
        'rate_limit': None,
        'timeout': 10
    },
    'alternative_me': {
        'base_url': 'https://api.alternative.me',
        'rate_limit': None,
        'timeout': 10
    }
}

# Cache Configuration (in seconds)
CACHE_DURATIONS = {
    'mstr_data': 1800,      # 30 minutes
    'crypto_prices': 60,     # 1 minute
    'whale_data': 300,       # 5 minutes
    'fear_greed': 3600,      # 1 hour
    'exchange_flows': 1800,  # 30 minutes
}

# Data Validation
VALIDATION_RULES = {
    'btc_price': {
        'min': 10000,
        'max': 1000000,
        'type': float
    },
    'eth_price': {
        'min': 100,
        'max': 100000,
        'type': float
    },
    'sol_price': {
        'min': 1,
        'max': 10000,
        'type': float
    },
    'mstr_price': {
        'min': 50,
        'max': 5000,
        'type': float
    },
    'whale_tx_min_btc': 10,  # Minimum BTC for whale transaction
    'max_api_retries': 3,
    'api_retry_delay': 2  # seconds
}

# MSTR Configuration
MSTR_CONFIG = {
    'btc_holdings': 632457,
    'shares_outstanding': 284.6e6,
    'strategy_url': 'https://www.strategy.com',
    'fallback_data': {
        'price': 334.41,
        'market_cap': 95187e6,
        'nav_premium': 60
    }
}

# Database Configuration
DATABASE_CONFIG = {
    'pragmas': [
        "PRAGMA journal_mode = WAL",
        "PRAGMA busy_timeout = 5000",
        "PRAGMA synchronous = NORMAL",
        "PRAGMA cache_size = -64000",
        "PRAGMA foreign_keys = ON",
        "PRAGMA temp_store = MEMORY",
        "PRAGMA mmap_size = 134217728",
        "PRAGMA optimize"
    ],
    'cleanup_days': 30,  # Delete data older than 30 days
    'vacuum_interval': 86400  # Run VACUUM every 24 hours
}

# WebSocket Configuration
WEBSOCKET_CONFIG = {
    'reconnect_attempts': 5,
    'reconnect_delay': 3,  # seconds
    'heartbeat_interval': 30,  # seconds
    'max_message_size': 1024 * 1024  # 1MB
}

# Application Settings
APP_CONFIG = {
    'host': '0.0.0.0',
    'port': 8000,
    'reload': False,
    'log_level': 'INFO',
    'update_intervals': {
        'price': 15,        # seconds
        'correlation': 30,  # seconds
        'whale': 30,        # seconds
        'microstructure': 60  # seconds
    }
}

# Technical Indicators Configuration
INDICATORS_CONFIG = {
    'rsi': {
        'period': 14,
        'overbought': 70,
        'oversold': 30
    },
    'macd': {
        'fast': 12,
        'slow': 26,
        'signal': 9
    },
    'bollinger': {
        'period': 20,
        'std_dev': 2
    },
    'ema_periods': [20, 50, 200],
    'volume_ma_period': 20
}

# Logging Configuration
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'btc_analyzer.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'default'
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console', 'file']
    }
}

# Exchange addresses for whale tracking
EXCHANGE_ADDRESSES = {
    'binance': [
        'bc1qm34lsc65zpw79lxes69zkqmk6ee3ewf0j77s3h',
        '1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s'
    ],
    'coinbase': [
        '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa',
        'bc1qa5wkgaew2dkv56kfvj49j0av5nml45x9ek9hz6'
    ],
    'kraken': [
        'bc1qjasf9z3h7w3jspkhtgatgpyvvzgpa2wwd2lr0eh5tx44reyn2k7sfc27a4'
    ]
}

def get_api_url(service, endpoint=''):
    """Get full API URL for a service"""
    base = API_CONFIG.get(service, {}).get('base_url', '')
    return f"{base}/{endpoint}" if endpoint else base

def validate_price(asset, price):
    """Validate price is within expected range"""
    rules = VALIDATION_RULES.get(f'{asset}_price', {})
    if not rules:
        return True
    
    min_val = rules.get('min', 0)
    max_val = rules.get('max', float('inf'))
    
    return min_val <= price <= max_val

# Export commonly used values
CACHE_DURATION_MSTR = CACHE_DURATIONS['mstr_data']
CACHE_DURATION_CRYPTO = CACHE_DURATIONS['crypto_prices']
CACHE_DURATION_WHALE = CACHE_DURATIONS['whale_data']
BTC_PRICE_MIN = VALIDATION_RULES['btc_price']['min']
BTC_PRICE_MAX = VALIDATION_RULES['btc_price']['max']
WHALE_TX_MIN = VALIDATION_RULES['whale_tx_min_btc']