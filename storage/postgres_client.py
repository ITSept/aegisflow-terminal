# storage/postgres_client.py
"""
Async PostgreSQL client for historical snapshots with logging.
"""

import asyncio
import logging
from typing import Optional

import asyncpg

from utils.logger import setup_logger

logger = setup_logger(__name__)


class PostgresClient:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None
        logger.info(f"PostgresClient created with DSN: {dsn[:30]}...")

    async def connect(self):
        """Create connection pool."""
        try:
            self.pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=5)
            logger.info("PostgreSQL connection pool created successfully")
        except Exception as e:
            logger.error(f"Failed to create PostgreSQL pool: {e}", exc_info=True)
            raise

    async def init_schema(self):
        """Create tables if they don't exist."""
        if not self.pool:
            logger.error("Cannot init schema: no database pool")
            return
        try:
            async with self.pool.acquire() as conn:
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
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS obi_snapshots (
                        id SERIAL PRIMARY KEY,
                        timestamp TIMESTAMPTZ DEFAULT NOW(),
                        obi REAL,
                        pressure TEXT
                    )
                """)
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
                logger.info("Database schema initialized (tables created if missing)")
        except Exception as e:
            logger.error(f"Failed to initialize schema: {e}", exc_info=True)
            raise

    async def insert_signal(self, obi: float, cvd: float, score: float, signal: str,
                            expansion_prob: str, aggression: str, pressure: str):
        """Insert one signal snapshot with logging."""
        if not self.pool:
            logger.error("Cannot insert signal: no database pool")
            return
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO signal_history (obi, cvd, score, signal, expansion_prob, aggression, pressure)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, obi, cvd, score, signal, expansion_prob, aggression, pressure)
                logger.debug(f"Signal inserted: score={score:.4f}, signal={signal}")
        except Exception as e:
            logger.error(f"Failed to insert signal: {e}", exc_info=True)

    async def insert_obi_snapshot(self, obi: float, pressure: str):
        if not self.pool:
            return
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("INSERT INTO obi_snapshots (obi, pressure) VALUES ($1, $2)", obi, pressure)
                logger.debug(f"OBI snapshot inserted: obi={obi:.4f}, pressure={pressure}")
        except Exception as e:
            logger.error(f"Failed to insert OBI snapshot: {e}", exc_info=True)

    async def insert_cvd_snapshot(self, buy_vol: float, sell_vol: float, delta: float, cvd: float, aggression: str):
        if not self.pool:
            return
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO cvd_snapshots (buy_vol, sell_vol, delta, cvd, aggression)
                    VALUES ($1, $2, $3, $4, $5)
                """, buy_vol, sell_vol, delta, cvd, aggression)
                logger.debug(f"CVD snapshot inserted: cvd={cvd:.2f}, aggression={aggression}")
        except Exception as e:
            logger.error(f"Failed to insert CVD snapshot: {e}", exc_info=True)

    async def close(self):
        if self.pool:
            await self.pool.close()
            logger.info("PostgreSQL pool closed")