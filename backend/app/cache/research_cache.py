"""Research result caching with TTL."""

import hashlib
import json
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any, Optional

from cachetools import TTLCache


class ResearchCache:
    """
    In-memory cache for research results with TTL.
    
    Features:
    - TTL-based expiration (default 24 hours)
    - Hash-based cache keys
    - Statistics tracking
    """

    def __init__(self, maxsize: int = 100, ttl_hours: int = 24):
        self.cache: TTLCache = TTLCache(
            maxsize=maxsize,
            ttl=ttl_hours * 3600,  # Convert to seconds
        )
        self.hits = 0
        self.misses = 0
        self.ttl_hours = ttl_hours

    def _make_key(self, topic: str, depth: str, include_academic: bool = False) -> str:
        """Generate cache key from research parameters."""
        key_data = f"{topic.lower().strip()}:{depth}:{include_academic}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]

    def get(
        self, 
        topic: str, 
        depth: str, 
        include_academic: bool = False
    ) -> Optional[dict[str, Any]]:
        """Get cached research result if available."""
        key = self._make_key(topic, depth, include_academic)
        result = self.cache.get(key)
        
        if result is not None:
            self.hits += 1
            return result
        
        self.misses += 1
        return None

    def set(
        self,
        topic: str,
        depth: str,
        result: dict[str, Any],
        include_academic: bool = False,
    ) -> None:
        """Cache a research result."""
        key = self._make_key(topic, depth, include_academic)
        self.cache[key] = {
            **result,
            "cached_at": datetime.utcnow().isoformat(),
            "cache_key": key,
        }

    def invalidate(self, topic: str, depth: str, include_academic: bool = False) -> bool:
        """Invalidate a specific cache entry."""
        key = self._make_key(topic, depth, include_academic)
        if key in self.cache:
            del self.cache[key]
            return True
        return False

    def clear(self) -> int:
        """Clear all cache entries. Returns count of cleared entries."""
        count = len(self.cache)
        self.cache.clear()
        return count

    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "size": len(self.cache),
            "maxsize": self.cache.maxsize,
            "ttl_hours": self.ttl_hours,
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 2),
        }


# Singleton cache instance
_cache_instance: Optional[ResearchCache] = None


def get_cache() -> ResearchCache:
    """Get the singleton cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = ResearchCache()
    return _cache_instance

