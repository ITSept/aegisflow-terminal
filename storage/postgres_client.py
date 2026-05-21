"""
Async PostgreSQL client for historical snapshots.
"""

import asyncpg
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class PostgresClient:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Create connection pool."""
        self.pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=5)
        logger.info("PostgreSQL pool created")

    async def init_schema(self):
        """Create tables if not exist."""
        async with self.pool.acquire() as conn:
            # Signal history
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS signal_history (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ DEFAULT NOW(),
                    obi REAL,
                    cvd REAL,
                    score REAL,
                    signal TEXT,
                    expansion_prob TEXT,
                    aggression TEXT,
                    pressure TEXT
                )
            """)
            # OBI snapshots
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS obi_snapshots (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ DEFAULT NOW(),
                    obi REAL,
                    pressure TEXT
                )
            """)
            # CVD snapshots
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS cvd_snapshots (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ DEFAULT NOW(),
                    buy_vol REAL,
                    sell_vol REAL,
                    delta REAL,
                    cvd REAL,
                    aggression TEXT
                )
            """)
            logger.info("Database schema initialized")

    async def insert_signal(self, obi: float, cvd: float, score: float, signal: str,
                            expansion_prob: str, aggression: str, pressure: str):
        """Insert one signal snapshot."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO signal_history (obi, cvd, score, signal, expansion_prob, aggression, pressure)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, obi, cvd, score, signal, expansion_prob, aggression, pressure)

    async def insert_obi_snapshot(self, obi: float, pressure: str):
        async with self.pool.acquire() as conn:
            await conn.execute("INSERT INTO obi_snapshots (obi, pressure) VALUES ($1, $2)", obi, pressure)

    async def insert_cvd_snapshot(self, buy_vol: float, sell_vol: float, delta: float, cvd: float, aggression: str):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO cvd_snapshots (buy_vol, sell_vol, delta, cvd, aggression)
                VALUES ($1, $2, $3, $4, $5)
            """, buy_vol, sell_vol, delta, cvd, aggression)

    async def close(self):
        if self.pool:
            await self.pool.close()
            logger.info("PostgreSQL pool closed")