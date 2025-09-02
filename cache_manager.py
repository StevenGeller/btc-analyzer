"""
Unified Cache Manager with TTL and Memory Management
"""
import time
import json
import pickle
from pathlib import Path
from typing import Any, Optional, Dict
import logging
from config import CACHE_DIR, CACHE_DURATIONS

logger = logging.getLogger(__name__)

class CacheManager:
    """Centralized cache management with TTL support"""
    
    def __init__(self):
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_dir = CACHE_DIR
        self.cache_dir.mkdir(exist_ok=True)
        self.max_memory_items = 1000
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0
        }
    
    def _get_cache_key(self, category: str, key: str) -> str:
        """Generate cache key"""
        return f"{category}:{key}"
    
    def get(self, category: str, key: str, default=None) -> Any:
        """Get cached value with TTL check"""
        cache_key = self._get_cache_key(category, key)
        
        # Check memory cache first
        if cache_key in self.memory_cache:
            entry = self.memory_cache[cache_key]
            if entry['expires_at'] > time.time():
                self.stats['hits'] += 1
                logger.debug(f"Cache hit (memory): {cache_key}")
                return entry['value']
            else:
                # Expired, remove it
                del self.memory_cache[cache_key]
        
        # Check disk cache
        cache_file = self.cache_dir / f"{cache_key.replace(':', '_')}.cache"
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    entry = pickle.load(f)
                    if entry['expires_at'] > time.time():
                        # Load to memory cache
                        self._add_to_memory(cache_key, entry)
                        self.stats['hits'] += 1
                        logger.debug(f"Cache hit (disk): {cache_key}")
                        return entry['value']
                    else:
                        # Expired, delete file
                        cache_file.unlink()
            except Exception as e:
                logger.error(f"Cache read error: {e}")
        
        self.stats['misses'] += 1
        logger.debug(f"Cache miss: {cache_key}")
        return default
    
    def set(self, category: str, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set cached value with TTL"""
        cache_key = self._get_cache_key(category, key)
        
        # Use default TTL from config if not specified
        if ttl is None:
            ttl = CACHE_DURATIONS.get(category, 300)  # Default 5 minutes
        
        entry = {
            'value': value,
            'timestamp': time.time(),
            'expires_at': time.time() + ttl
        }
        
        # Save to memory cache
        self._add_to_memory(cache_key, entry)
        
        # Save to disk cache for persistence
        cache_file = self.cache_dir / f"{cache_key.replace(':', '_')}.cache"
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(entry, f)
            logger.debug(f"Cache set: {cache_key} (TTL: {ttl}s)")
        except Exception as e:
            logger.error(f"Cache write error: {e}")
    
    def _add_to_memory(self, cache_key: str, entry: Dict) -> None:
        """Add to memory cache with LRU eviction"""
        # Evict if at capacity
        if len(self.memory_cache) >= self.max_memory_items:
            # Remove oldest entry
            oldest_key = min(self.memory_cache.keys(), 
                           key=lambda k: self.memory_cache[k]['timestamp'])
            del self.memory_cache[oldest_key]
            self.stats['evictions'] += 1
        
        self.memory_cache[cache_key] = entry
    
    def delete(self, category: str, key: str) -> None:
        """Delete cached value"""
        cache_key = self._get_cache_key(category, key)
        
        # Remove from memory
        if cache_key in self.memory_cache:
            del self.memory_cache[cache_key]
        
        # Remove from disk
        cache_file = self.cache_dir / f"{cache_key.replace(':', '_')}.cache"
        if cache_file.exists():
            cache_file.unlink()
    
    def clear_category(self, category: str) -> None:
        """Clear all cache entries for a category"""
        # Clear memory cache
        keys_to_delete = [k for k in self.memory_cache.keys() 
                         if k.startswith(f"{category}:")]
        for key in keys_to_delete:
            del self.memory_cache[key]
        
        # Clear disk cache
        for cache_file in self.cache_dir.glob(f"{category}_*.cache"):
            cache_file.unlink()
        
        logger.info(f"Cleared cache category: {category}")
    
    def clear_expired(self) -> int:
        """Clear all expired cache entries"""
        current_time = time.time()
        expired_count = 0
        
        # Clear expired from memory
        expired_keys = [k for k, v in self.memory_cache.items() 
                       if v['expires_at'] <= current_time]
        for key in expired_keys:
            del self.memory_cache[key]
            expired_count += 1
        
        # Clear expired from disk
        for cache_file in self.cache_dir.glob("*.cache"):
            try:
                with open(cache_file, 'rb') as f:
                    entry = pickle.load(f)
                    if entry['expires_at'] <= current_time:
                        cache_file.unlink()
                        expired_count += 1
            except Exception:
                # Corrupted file, delete it
                cache_file.unlink()
                expired_count += 1
        
        if expired_count > 0:
            logger.info(f"Cleared {expired_count} expired cache entries")
        
        return expired_count
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'evictions': self.stats['evictions'],
            'hit_rate': f"{hit_rate:.1f}%",
            'memory_items': len(self.memory_cache),
            'disk_files': len(list(self.cache_dir.glob("*.cache")))
        }
    
    def get_or_set(self, category: str, key: str, 
                   fetch_func, ttl: Optional[int] = None) -> Any:
        """Get from cache or fetch and cache"""
        value = self.get(category, key)
        if value is not None:
            return value
        
        # Fetch fresh data
        try:
            value = fetch_func()
            if value is not None:
                self.set(category, key, value, ttl)
            return value
        except Exception as e:
            logger.error(f"Fetch function error: {e}")
            return None

# Singleton instance
_cache_manager = None

def get_cache_manager() -> CacheManager:
    """Get or create cache manager instance"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager

# Decorator for caching function results
def cached(category: str, ttl: Optional[int] = None):
    """Decorator to cache function results"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            cache = get_cache_manager()
            
            # Create cache key from function name and arguments
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try to get from cache
            result = cache.get(category, key)
            if result is not None:
                return result
            
            # Call function and cache result
            result = func(*args, **kwargs)
            if result is not None:
                cache.set(category, key, result, ttl)
            
            return result
        return wrapper
    return decorator

if __name__ == "__main__":
    # Test cache manager
    cache = get_cache_manager()
    
    # Test set and get
    cache.set('test', 'key1', {'data': 'value1'}, ttl=5)
    print(f"Get key1: {cache.get('test', 'key1')}")
    
    # Test expiration
    time.sleep(6)
    print(f"Get key1 after expiry: {cache.get('test', 'key1')}")
    
    # Test stats
    print(f"Cache stats: {cache.get_stats()}")
    
    # Clear expired
    cache.clear_expired()
    print("Cleared expired entries")