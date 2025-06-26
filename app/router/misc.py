import asyncio
import datetime
import logging
import os
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.requests import Request
from pydantic import BaseModel
from playwright.async_api import Browser

from settings import REVISION, BROWSER_CONTEXT_LIMIT
from internal import redis_cache
from server.auth import AuthRequired


router = APIRouter(tags=['misc'])


class PingData(BaseModel):
    browserType: Annotated[str, Query(description='the browser type (chromium, firefox or webkit)')]
    browserVersion: Annotated[str, Query(description='the browser version')]
    browserContextLimit: Annotated[int, Query(description='the maximum number of browser contexts (aka tabs)')]
    browserContextUsed: Annotated[int, Query(description='the number of all open browser contexts')]
    availableSlots: Annotated[int, Query(description='the number of available browser contexts')]
    isConnected: Annotated[bool, Query(description='indicates that the browser is connected')]
    now: Annotated[datetime.datetime, Query(description='UTC time now')]
    revision: Annotated[str, Query(description='the scrapper revision')]


@router.get('/ping', summary='Ping the Scrapper', response_model=PingData)
async def ping(request: Request) -> dict:
    """
    The ping endpoint checks if the Scrapper is running, both from Docker and externally.
    """
    browser: Browser = request.state.browser
    semaphore: asyncio.Semaphore = request.state.semaphore

    now = datetime.datetime.now(datetime.timezone.utc)

    return {
        'browserType': browser.browser_type.name,
        'browserVersion': browser.version,
        'browserContextLimit': BROWSER_CONTEXT_LIMIT,
        'browserContextUsed': len(browser.contexts),
        'availableSlots': semaphore._value,
        'isConnected': browser.is_connected(),
        'now': now,
        'revision': REVISION,
    }


@router.get('/health', summary='Health check', include_in_schema=False)
async def health_check():
    """Health check endpoint"""
    return {'status': 'ok', 'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat()}


@router.get('/cache-stats', summary='Get cache statistics and Redis status')
async def cache_stats(
    _: AuthRequired,
) -> dict:
    """
    Get comprehensive cache statistics including Redis status, 
    migration phase, and performance metrics.
    """
    try:
        # Get Redis cache statistics
        stats = redis_cache.get_cache().get_stats()
        
        # Add environment information
        stats.update({
            'redis_url': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
            'redis_enabled_env': os.getenv('REDIS_ENABLED', 'false'),
            'migration_phase_env': os.getenv('REDIS_MIGRATION_PHASE', '1'),
        })
        
        # Calculate hit rate if available
        if 'redis_keyspace_hits' in stats and 'redis_keyspace_misses' in stats:
            hits = stats['redis_keyspace_hits']
            misses = stats['redis_keyspace_misses']
            total = hits + misses
            if total > 0:
                stats['redis_hit_rate'] = round((hits / total) * 100, 2)
            else:
                stats['redis_hit_rate'] = 0
        
        return {
            'success': True,
            'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'cache_stats': stats
        }
        
    except Exception as e:
        logging.error(f"Error getting cache stats: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat()
        }


@router.get('/cache-cleanup', summary='Clean up expired cache entries')
async def cache_cleanup(
    _: AuthRequired,
) -> dict:
    """
    Manually trigger cache cleanup for expired entries.
    Redis handles TTL automatically, but this can be useful for file cache cleanup.
    """
    try:
        cleaned_count = redis_cache.get_cache().cleanup_expired()
        
        return {
            'success': True,
            'cleaned_entries': cleaned_count,
            'message': f'Cleaned up {cleaned_count} expired cache entries',
            'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        
    except Exception as e:
        logging.error(f"Error during cache cleanup: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
