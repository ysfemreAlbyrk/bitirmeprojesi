"""Redis client wrapper for caching and session management"""
import redis.asyncio as redis
from typing import Optional, Any
import json
from config import settings


class RedisClient:
    """Singleton Redis client with async support"""
    
    _instance: Optional['RedisClient'] = None
    _client: Optional[redis.Redis] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def connect(self):
        """Establish Redis connection"""
        if self._client is None:
            self._client = await redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                health_check_interval=30
            )
    
    async def disconnect(self):
        """Close Redis connection"""
        if self._client:
            await self._client.close()
            self._client = None
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis"""
        if not self._client:
            await self.connect()
        return await self._client.get(key)
    
    async def set(self, key: str, value: str, ex: Optional[int] = None):
        """Set value in Redis with optional expiration"""
        if not self._client:
            await self.connect()
        await self._client.set(key, value, ex=ex)
    
    async def delete(self, key: str):
        """Delete key from Redis"""
        if not self._client:
            await self.connect()
        await self._client.delete(key)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis"""
        if not self._client:
            await self.connect()
        return await self._client.exists(key) > 0
    
    async def get_json(self, key: str) -> Optional[Any]:
        """Get JSON value from Redis"""
        value = await self.get(key)
        if value:
            return json.loads(value)
        return None
    
    async def set_json(self, key: str, value: Any, ex: Optional[int] = None):
        """Set JSON value in Redis with optional expiration"""
        json_value = json.dumps(value)
        await self.set(key, json_value, ex=ex)
    
    async def incr(self, key: str) -> int:
        """Increment counter"""
        if not self._client:
            await self.connect()
        return await self._client.incr(key)
    
    async def expire(self, key: str, seconds: int):
        """Set expiration for key"""
        if not self._client:
            await self.connect()
        await self._client.expire(key, seconds)
    
    async def ttl(self, key: str) -> int:
        """Get time to live for key"""
        if not self._client:
            await self.connect()
        return await self._client.ttl(key)
    
    async def ping(self) -> bool:
        """Check Redis connection"""
        if not self._client:
            await self.connect()
        try:
            return await self._client.ping()
        except Exception:
            return False


# Global instance
redis_client = RedisClient()
