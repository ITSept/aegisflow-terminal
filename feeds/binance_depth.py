# feeds/binance_depth.py
"""
Binance Futures Depth Stream (REST polling fallback) with comprehensive logging.
Fetches orderbook every `interval` seconds and calls callback with parsed depth.
"""

import asyncio
import aiohttp
import logging
from datetime import datetime
from typing import Callable, Optional, List

from utils.logger import setup_logger

logger = setup_logger(__name__)

class BinanceDepthStream:
    """
    Fetches orderbook depth from Binance Futures REST API at regular intervals.
    Calls on_depth(depth) callback where depth contains bids/asks lists.
    """

    def __init__(self, symbol: str = "btcusdt", interval: float = 1.0, on_depth: Optional[Callable] = None):
        """
        Args:
            symbol: Trading pair, e.g. 'btcusdt' (will be uppercased for API)
            interval: Polling interval in seconds (default 1.0)
            on_depth: Async callback function that receives depth dict
        """
        self.symbol = symbol.upper()
        self.interval = interval
        self.on_depth = on_depth
        self.url = f"https://fapi.binance.com/fapi/v1/depth?symbol={self.symbol}&limit=20"
        self.session: Optional[aiohttp.ClientSession] = None
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
        self._request_count = 0
        self._error_count = 0

    async def _fetch_depth(self) -> Optional[dict]:
        """Fetch one depth snapshot from REST API."""
        if not self.session:
            logger.error("No active HTTP session")
            return None

        try:
            async with self.session.get(self.url, timeout=5) as resp:
                self._request_count += 1
                if resp.status == 200:
                    data = await resp.json()
                    bids = [[float(price), float(qty)] for price, qty in data.get('bids', [])]
                    asks = [[float(price), float(qty)] for price, qty in data.get('asks', [])]
                    logger.debug(f"Depth fetched: {len(bids)} bids, {len(asks)} asks (request #{self._request_count})")
                    return {
                        "bids": bids,
                        "asks": asks,
                        "update_time": data.get("E", int(datetime.now().timestamp() * 1000))
                    }
                else:
                    logger.error(f"Depth API error {resp.status}: {resp.reason}")
                    self._error_count += 1
                    return None
        except asyncio.TimeoutError:
            logger.error("Depth fetch timeout")
            self._error_count += 1
            return None
        except aiohttp.ClientError as e:
            logger.error(f"Depth HTTP client error: {e}")
            self._error_count += 1
            return None
        except Exception as e:
            logger.exception(f"Unexpected depth fetch error: {e}")
            self._error_count += 1
            return None

    async def _poll_loop(self):
        """Main polling loop."""
        logger.info(f"Depth polling started for {self.symbol}, interval={self.interval}s")
        while self.is_running:
            loop_start = asyncio.get_event_loop().time()
            depth = await self._fetch_depth()
            if depth and self.on_depth:
                try:
                    await self.on_depth(depth)
                except Exception as e:
                    logger.exception(f"Depth callback error: {e}")
            # Sleep remaining time to maintain interval as close as possible
            elapsed = asyncio.get_event_loop().time() - loop_start
            sleep_time = max(0, self.interval - elapsed)
            await asyncio.sleep(sleep_time)
        logger.info("Depth polling stopped")

    async def start(self):
        """Start the polling task."""
        if self.is_running:
            logger.warning("Depth stream already running")
            return
        self.is_running = True
        self.session = aiohttp.ClientSession()
        self.task = asyncio.create_task(self._poll_loop())
        logger.info("Depth stream started")

    async def stop(self):
        """Stop the polling task and clean up."""
        if not self.is_running:
            return
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        if self.session:
            await self.session.close()
        logger.info(f"Depth stream stopped (total requests: {self._request_count}, errors: {self._error_count})")

    def get_stats(self) -> dict:
        """Return statistics about polling."""
        return {
            "total_requests": self._request_count,
            "total_errors": self._error_count,
            "error_rate": self._error_count / self._request_count if self._request_count else 0
        }