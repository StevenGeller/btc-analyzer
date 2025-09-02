"""
Data Validation and Sanitization Module
Ensures data integrity and prevents bad data from entering the system
"""
import logging
from typing import Any, Dict, Optional, Union
from datetime import datetime
import numpy as np
from config import VALIDATION_RULES, BTC_PRICE_MIN, BTC_PRICE_MAX

logger = logging.getLogger(__name__)

class DataValidator:
    """Validate and sanitize incoming data"""
    
    @staticmethod
    def validate_price(asset: str, price: Any) -> Optional[float]:
        """Validate cryptocurrency price"""
        try:
            price = float(price)
            
            # Check for invalid values
            if not np.isfinite(price) or price <= 0:
                logger.warning(f"Invalid {asset} price: {price}")
                return None
            
            # Asset-specific validation
            if asset.lower() == 'btc':
                if not (BTC_PRICE_MIN <= price <= BTC_PRICE_MAX):
                    logger.warning(f"BTC price out of range: ${price}")
                    return None
            elif asset.lower() == 'eth':
                if not (100 <= price <= 100000):
                    logger.warning(f"ETH price out of range: ${price}")
                    return None
            elif asset.lower() == 'sol':
                if not (1 <= price <= 10000):
                    logger.warning(f"SOL price out of range: ${price}")
                    return None
            elif asset.lower() == 'mstr':
                if not (50 <= price <= 5000):
                    logger.warning(f"MSTR price out of range: ${price}")
                    return None
            
            return round(price, 2)
            
        except (TypeError, ValueError) as e:
            logger.error(f"Price validation error for {asset}: {e}")
            return None
    
    @staticmethod
    def validate_volume(volume: Any) -> Optional[float]:
        """Validate trading volume"""
        try:
            volume = float(volume)
            
            if not np.isfinite(volume) or volume < 0:
                logger.warning(f"Invalid volume: {volume}")
                return None
            
            # Volume sanity check (max $1 trillion)
            if volume > 1e12:
                logger.warning(f"Volume exceeds maximum: {volume}")
                return None
            
            return round(volume, 2)
            
        except (TypeError, ValueError) as e:
            logger.error(f"Volume validation error: {e}")
            return None
    
    @staticmethod
    def validate_percentage(value: Any, name: str = "percentage") -> Optional[float]:
        """Validate percentage values"""
        try:
            value = float(value)
            
            if not np.isfinite(value):
                logger.warning(f"Invalid {name}: {value}")
                return None
            
            # Most percentages should be within -100% to +1000%
            if not (-100 <= value <= 1000):
                logger.warning(f"{name} out of range: {value}%")
                return None
            
            return round(value, 2)
            
        except (TypeError, ValueError) as e:
            logger.error(f"Percentage validation error for {name}: {e}")
            return None
    
    @staticmethod
    def validate_timestamp(timestamp: Any) -> Optional[int]:
        """Validate timestamp"""
        try:
            timestamp = int(timestamp)
            
            # Check if timestamp is reasonable (between 2009 and 2030)
            min_ts = int(datetime(2009, 1, 1).timestamp())
            max_ts = int(datetime(2030, 1, 1).timestamp())
            
            if not (min_ts <= timestamp <= max_ts):
                logger.warning(f"Timestamp out of range: {timestamp}")
                return None
            
            return timestamp
            
        except (TypeError, ValueError) as e:
            logger.error(f"Timestamp validation error: {e}")
            return None
    
    @staticmethod
    def validate_whale_transaction(tx_data: Dict) -> Optional[Dict]:
        """Validate whale transaction data"""
        validated = {}
        
        # Validate amount
        amount = tx_data.get('amount_btc', 0)
        try:
            amount = float(amount)
            if amount < VALIDATION_RULES['whale_tx_min_btc']:
                return None  # Not a whale transaction
            if amount > 1000000:  # Max 1M BTC (sanity check)
                logger.warning(f"Transaction amount too large: {amount} BTC")
                return None
            validated['amount_btc'] = round(amount, 8)
        except (TypeError, ValueError):
            return None
        
        # Validate USD value
        usd_value = tx_data.get('usd_value', 0)
        try:
            usd_value = float(usd_value)
            if usd_value < 0 or usd_value > 1e12:  # Max $1 trillion
                return None
            validated['usd_value'] = round(usd_value, 2)
        except (TypeError, ValueError):
            validated['usd_value'] = validated['amount_btc'] * 100000  # Estimate
        
        # Validate timestamp
        timestamp = DataValidator.validate_timestamp(
            tx_data.get('timestamp', int(datetime.now().timestamp()))
        )
        if timestamp:
            validated['timestamp'] = timestamp
        
        # Copy other fields
        validated['tx_hash'] = str(tx_data.get('tx_hash', ''))[:100]  # Limit length
        validated['type'] = str(tx_data.get('type', 'unknown'))[:50]
        
        return validated
    
    @staticmethod
    def validate_market_data(data: Dict) -> Dict:
        """Validate complete market data structure"""
        validated = {}
        
        # Validate BTC price
        if 'btc_price' in data:
            price = DataValidator.validate_price('btc', data['btc_price'])
            if price:
                validated['btc_price'] = price
        
        # Validate other prices
        for asset in ['eth', 'sol', 'mstr']:
            key = f'{asset}_price'
            if key in data:
                price = DataValidator.validate_price(asset, data[key])
                if price:
                    validated[key] = price
        
        # Validate volumes
        if 'volume' in data:
            volume = DataValidator.validate_volume(data['volume'])
            if volume:
                validated['volume'] = volume
        
        # Validate percentages
        for key in ['price_change_24h', 'nav_premium', 'alpha']:
            if key in data:
                value = DataValidator.validate_percentage(data[key], key)
                if value is not None:
                    validated[key] = value
        
        # Validate RSI (0-100)
        if 'rsi' in data:
            try:
                rsi = float(data['rsi'])
                if 0 <= rsi <= 100:
                    validated['rsi'] = round(rsi, 1)
            except (TypeError, ValueError):
                pass
        
        return validated
    
    @staticmethod
    def sanitize_string(text: Any, max_length: int = 1000) -> str:
        """Sanitize string input"""
        if text is None:
            return ""
        
        # Convert to string and limit length
        text = str(text)[:max_length]
        
        # Remove potential SQL injection attempts
        dangerous_patterns = ['DROP', 'DELETE', 'INSERT', 'UPDATE', '--', '/*', '*/']
        for pattern in dangerous_patterns:
            text = text.replace(pattern, '')
        
        return text.strip()
    
    @staticmethod
    def validate_api_response(response: Dict, required_fields: list) -> bool:
        """Validate API response has required fields"""
        if not isinstance(response, dict):
            logger.error("API response is not a dictionary")
            return False
        
        missing_fields = [field for field in required_fields 
                         if field not in response or response[field] is None]
        
        if missing_fields:
            logger.warning(f"API response missing fields: {missing_fields}")
            return False
        
        return True

class DataSanitizer:
    """Sanitize data before storage or display"""
    
    @staticmethod
    def clean_for_json(data: Any) -> Any:
        """Clean data for JSON serialization"""
        if isinstance(data, dict):
            return {k: DataSanitizer.clean_for_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [DataSanitizer.clean_for_json(item) for item in data]
        elif isinstance(data, (int, str, bool, type(None))):
            return data
        elif isinstance(data, float):
            # Handle NaN and Infinity
            if np.isnan(data) or np.isinf(data):
                return None
            return round(data, 8)
        else:
            return str(data)
    
    @staticmethod
    def clean_database_row(row: Dict) -> Dict:
        """Clean database row for safe usage"""
        cleaned = {}
        for key, value in row.items():
            if value is None:
                cleaned[key] = None
            elif isinstance(value, (int, float)):
                if isinstance(value, float) and not np.isfinite(value):
                    cleaned[key] = None
                else:
                    cleaned[key] = value
            else:
                cleaned[key] = DataValidator.sanitize_string(value)
        return cleaned

# Validation decorators
def validate_input(**validators):
    """Decorator to validate function inputs"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Validate kwargs based on validators
            for param, validator_func in validators.items():
                if param in kwargs:
                    validated = validator_func(kwargs[param])
                    if validated is None:
                        logger.error(f"Validation failed for {param} in {func.__name__}")
                        return None
                    kwargs[param] = validated
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

if __name__ == "__main__":
    # Test validators
    validator = DataValidator()
    
    # Test price validation
    print(f"BTC $108000: {validator.validate_price('btc', 108000)}")
    print(f"BTC $-100: {validator.validate_price('btc', -100)}")
    print(f"ETH $4400: {validator.validate_price('eth', 4400)}")
    
    # Test percentage validation
    print(f"5.5%: {validator.validate_percentage(5.5)}")
    print(f"2000%: {validator.validate_percentage(2000)}")
    
    # Test market data validation
    market_data = {
        'btc_price': 108500,
        'eth_price': 4400,
        'volume': 1e9,
        'price_change_24h': -0.5,
        'rsi': 48.5
    }
    print(f"Market data: {validator.validate_market_data(market_data)}")
    
    # Test sanitization
    sanitizer = DataSanitizer()
    dirty_data = {
        'price': 100.0,
        'nan_value': float('nan'),
        'inf_value': float('inf'),
        'text': 'DROP TABLE users; --'
    }
    print(f"Cleaned data: {sanitizer.clean_for_json(dirty_data)}")