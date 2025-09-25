import aioredis
import json
from typing import Optional, Any
from src.config import Config

JTI_EXPIRY = 3600
CACHE_EXPIRY = 300  # 5 minutes for general cache

token_blocklist = aioredis.from_url(Config.REDIS_URL)
cache = aioredis.from_url(Config.REDIS_URL, db=1)  # Use different DB for caching


async def add_jti_to_blocklist(jti: str) -> None:
    await token_blocklist.set(name=jti, value="", ex=JTI_EXPIRY)


async def token_in_blocklist(jti:str) -> bool:
    jti = await token_blocklist.get(jti)
    return jti is not None


# Cache functions
async def get_cache(key: str) -> Optional[Any]:
    """Get value from cache"""
    try:
        value = await cache.get(key)
        if value:
            return json.loads(value)
        return None
    except Exception:
        return None


async def set_cache(key: str, value: Any, expiry: int = CACHE_EXPIRY) -> None:
    """Set value in cache"""
    try:
        await cache.set(key, json.dumps(value, default=str), ex=expiry)
    except Exception:
        pass  # Fail silently for cache operations


async def delete_cache(key: str) -> None:
    """Delete value from cache"""
    try:
        await cache.delete(key)
    except Exception:
        pass


async def delete_cache_pattern(pattern: str) -> None:
    """Delete all keys matching pattern"""
    try:
        keys = await cache.keys(pattern)
        if keys:
            await cache.delete(*keys)
    except Exception:

        pass
