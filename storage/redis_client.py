"""
Async Redis client for caching latest state.
"""

import json
import logging
import redis.asyncio as redis
from typing import Optional

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0, password: Optional[str] = None):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.redis: Optional[redis.Redis] = None

    async def connect(self):
        """Establish connection."""
        self.redis = await redis.from_url(
            f"redis://{self.host}:{self.port}/{self.db}",
            password=self.password,
            decode_responses=True
        )
        await self.redis.ping()
        logger.info(f"Redis connected to {self.host}:{self.port}")

    async def set_latest(self, key: str, value: dict, expire: int = 3600):
        """Store latest state as JSON with optional TTL (seconds)."""
        if self.redis:
            await self.redis.setex(f"latest:{key}", expire, json.dumps(value))

    async def get_latest(self, key: str) -> Optional[dict]:
        """Retrieve latest state."""
        if self.redis:
            data = await self.redis.get(f"latest:{key}")
            return json.loads(data) if data else None
        return None

    async def close(self):
        if self.redis:
            await self.redis.close()
            logger.info("Redis connection closed")