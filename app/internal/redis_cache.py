"""
Redis Cache Implementation for Scrapper v2.1

This module provides Redis-based caching with fallback to file system,
implementing incremental migration strategy.
"""

import json
import logging
import os
from typing import Any, Dict, Optional
from datetime import datetime, timedelta

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from . import cache as file_cache
from .util import normalize_url


logger = logging.getLogger(__name__)


class RedisCache:
    """
    Redis-based cache with file system fallback.
    
    Implements incremental migration:
    - Phase 1: Redis as secondary cache (fallback to file)
    - Phase 2: Redis as primary cache (file as backup) 
    - Phase 3: Redis only
    """
    
    def __init__(self):
        self.redis_client = None
        self.redis_enabled = False
        self.phase = 1  # Migration phase (1, 2, or 3)
        
        # Initialize Redis connection
        self._init_redis()
        
        # Set migration phase based on Redis availability
        if self.redis_enabled:
            self.phase = int(os.getenv('REDIS_MIGRATION_PHASE', '1'))
            logger.info(f"Redis cache initialized - Phase {self.phase}")
        else:
            logger.warning("Redis not available - using file cache only")
    
    def _init_redis(self):
        """Initialize Redis connection with error handling"""
        redis_enabled_env = os.getenv('REDIS_ENABLED', 'false').lower()
        logging.info(f"[redis_cache] REDIS_ENABLED={redis_enabled_env}")
        if not REDIS_AVAILABLE:
            logging.warning("Redis library not available")
            return
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        redis_enabled = redis_enabled_env == 'true'
        logging.info(f"[redis_cache] REDIS_ENABLED parsed: {redis_enabled}, REDIS_URL={redis_url}")
        if not redis_enabled:
            logging.info("Redis disabled via REDIS_ENABLED=false")
            return
        try:
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            # Test connection
            self.redis_client.ping()
            self.redis_enabled = True
            logging.info(f"Redis connected successfully: {redis_url}")
        except Exception as e:
            logging.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
            self.redis_enabled = False
    
    def make_key(self, path: str) -> str:
        """Generate cache key using normalized URL"""
        normalized = normalize_url(path)
        return file_cache.make_key(normalized)
    
    def store_result(self, key: str, data: Dict[str, Any], ttl: int = 3600) -> bool:
        """
        Store result with TTL.
        
        Migration phases:
        - Phase 1: Store in both Redis and file (Redis as backup)
        - Phase 2: Store primarily in Redis, file as backup
        - Phase 3: Store only in Redis
        """
        success = False
        
        try:
            if self.redis_enabled and self.phase >= 1:
                # Store in Redis with TTL
                redis_key = f"scrape_result:{key}"
                
                # Store metadata
                metadata = {
                    'stored_at': datetime.now().isoformat(),
                    'ttl': ttl,
                    'phase': self.phase
                }
                
                # Store main data as JSON
                self.redis_client.hset(redis_key, mapping={
                    'data': json.dumps(data),
                    'metadata': json.dumps(metadata)
                })
                
                # Set TTL
                self.redis_client.expire(redis_key, ttl)
                
                logger.debug(f"Stored result in Redis: {redis_key} (TTL: {ttl}s)")
                success = True
                
        except Exception as e:
            logger.error(f"Failed to store in Redis: {e}")
            success = False
        
        # File system backup (phases 1 and 2)
        if self.phase <= 2:
            try:
                file_cache.store_result(key, data)
                logger.debug(f"Stored result in file cache: {key}")
                success = True
            except Exception as e:
                logger.error(f"Failed to store in file cache: {e}")
                if not success:  # Only fail if Redis also failed
                    raise
        
        return success
    
    def load_result(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Load result with fallback strategy.
        
        Migration phases:
        - Phase 1: Try Redis first, fallback to file
        - Phase 2: Try Redis first, fallback to file  
        - Phase 3: Redis only
        """
        
        # Try Redis first (all phases)
        if self.redis_enabled and self.phase >= 1:
            try:
                redis_key = f"scrape_result:{key}"
                result = self.redis_client.hgetall(redis_key)
                
                if result and 'data' in result:
                    data = json.loads(result['data'])
                    metadata = json.loads(result.get('metadata', '{}'))
                    
                    logger.debug(f"Loaded result from Redis: {redis_key}")
                    return data
                    
            except Exception as e:
                logger.error(f"Failed to load from Redis: {e}")
        
        # Fallback to file system (phases 1 and 2)
        if self.phase <= 2:
            try:
                result = file_cache.load_result(key)
                if result:
                    logger.debug(f"Loaded result from file cache: {key}")
                    
                    # If Redis is available, store in Redis for next time
                    if self.redis_enabled and self.phase >= 1:
                        try:
                            self.store_result(key, result, ttl=3600)
                            logger.debug(f"Migrated result to Redis: {key}")
                        except Exception as e:
                            logger.error(f"Failed to migrate to Redis: {e}")
                    
                    return result
                    
            except Exception as e:
                logger.error(f"Failed to load from file cache: {e}")
        
        return None
    
    def delete_result(self, key: str) -> bool:
        """Delete result from all caches"""
        success = False
        
        # Delete from Redis
        if self.redis_enabled and self.phase >= 1:
            try:
                redis_key = f"scrape_result:{key}"
                deleted = self.redis_client.delete(redis_key)
                if deleted:
                    logger.debug(f"Deleted from Redis: {redis_key}")
                    success = True
            except Exception as e:
                logger.error(f"Failed to delete from Redis: {e}")
        
        # Delete from file system
        if self.phase <= 2:
            try:
                file_deleted = file_cache.delete_result(key)
                if file_deleted:
                    logger.debug(f"Deleted from file cache: {key}")
                    success = True
            except Exception as e:
                logger.error(f"Failed to delete from file cache: {e}")
        
        return success
    
    def exists(self, key: str) -> bool:
        """Check if result exists in any cache"""
        
        # Check Redis first
        if self.redis_enabled and self.phase >= 1:
            try:
                redis_key = f"scrape_result:{key}"
                if self.redis_client.exists(redis_key):
                    return True
            except Exception as e:
                logger.error(f"Failed to check Redis existence: {e}")
        
        # Check file system
        if self.phase <= 2:
            try:
                return file_cache.exists(key)
            except Exception as e:
                logger.error(f"Failed to check file cache existence: {e}")
        
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = {
            'redis_enabled': self.redis_enabled,
            'migration_phase': self.phase,
            'redis_available': REDIS_AVAILABLE
        }
        
        if self.redis_enabled:
            try:
                info = self.redis_client.info()
                stats.update({
                    'redis_memory_used': info.get('used_memory_human', 'Unknown'),
                    'redis_connected_clients': info.get('connected_clients', 0),
                    'redis_total_commands': info.get('total_commands_processed', 0),
                    'redis_keyspace_hits': info.get('keyspace_hits', 0),
                    'redis_keyspace_misses': info.get('keyspace_misses', 0)
                })
                
                # Count scrape results
                scrape_keys = self.redis_client.keys('scrape_result:*')
                stats['redis_scrape_results'] = len(scrape_keys)
                
            except Exception as e:
                logger.error(f"Failed to get Redis stats: {e}")
                stats['redis_error'] = str(e)
        
        return stats
    
    def cleanup_expired(self) -> int:
        """Clean up expired entries (Redis handles this automatically via TTL)"""
        cleaned = 0
        
        if self.redis_enabled:
            # Redis handles TTL automatically, but we can check for manual cleanup
            try:
                # Get all scrape result keys
                keys = self.redis_client.keys('scrape_result:*')
                logger.debug(f"Found {len(keys)} Redis cache entries")
                
                # Redis TTL cleanup is automatic, just return count
                return len(keys)
                
            except Exception as e:
                logger.error(f"Failed to check Redis keys: {e}")
        
        # File system cleanup (phases 1 and 2)
        if self.phase <= 2:
            try:
                cleaned = file_cache.cleanup_expired()
                logger.debug(f"Cleaned {cleaned} expired file cache entries")
            except Exception as e:
                logger.error(f"Failed to cleanup file cache: {e}")
        
        return cleaned


# Global cache instance
_redis_cache_instance = None


def get_cache() -> RedisCache:
    """Get global Redis cache instance"""
    global _redis_cache_instance
    if _redis_cache_instance is None:
        _redis_cache_instance = RedisCache()
    return _redis_cache_instance


# Compatibility functions for existing code
def make_key(path: str) -> str:
    """Compatibility function"""
    return get_cache().make_key(path)


def store_result(key: str, data: Dict[str, Any]) -> bool:
    """Compatibility function"""
    return get_cache().store_result(key, data)


def load_result(key: str) -> Optional[Dict[str, Any]]:
    """Compatibility function"""
    return get_cache().load_result(key)


def delete_result(key: str) -> bool:
    """Compatibility function"""
    return get_cache().delete_result(key)


def exists(key: str) -> bool:
    """Compatibility function"""
    return get_cache().exists(key) 