"""
Binance Futures Depth (REST polling fallback)
- Mengambil orderbook setiap 1 detik via REST API
- Memanggil callback on_depth dengan format yang sama seperti WebSocket
- Reconnect handling sederhana via retry
"""

import asyncio
import aiohttp
import logging
from typing import Callable, Optional, List

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class BinanceDepthStream:
    def __init__(self, symbol: str = "btcusdt", on_depth: Optional[Callable] = None, interval: float = 1.0):
        self.symbol = symbol.upper()
        self.url = f"https://fapi.binance.com/fapi/v1/depth?symbol={self.symbol}&limit=20"
        self.on_depth = on_depth
        self.interval = interval  # detik antar polling
        self.is_running = False
        self.session = None
        self.reconnect_delay = 3
        self.max_reconnect_delay = 30

    async def _fetch_depth(self) -> dict:
        """Fetch orderbook dari REST API"""
        try:
            async with self.session.get(self.url) as response:
                if response.status == 200:
                    data = await response.json()
                    # Format seperti WebSocket: { "bids": [[price, qty], ...], "asks": [...] }
                    bids = [[float(price), float(qty)] for price, qty in data.get('bids', [])]
                    asks = [[float(price), float(qty)] for price, qty in data.get('asks', [])]
                    return {"bids": bids, "asks": asks, "update_time": data.get("E", 0)}
                else:
                    logger.error(f"Depth API error: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Depth fetch error: {e}")
            return None

    async def _poll_loop(self):
        """Loop polling setiap interval detik"""
        while self.is_running:
            if self.session is None or self.session.closed:
                self.session = aiohttp.ClientSession()
            depth = await self._fetch_depth()
            if depth and self.on_depth:
                await self.on_depth(depth)
            await asyncio.sleep(self.interval)

    async def start(self):
        """Mulai polling depth"""
        self.is_running = True
        self.session = aiohttp.ClientSession()
        logger.info(f"Depth polling started for {self.symbol}, interval={self.interval}s")
        try:
            await self._poll_loop()
        except Exception as e:
            logger.error(f"Depth polling loop error: {e}")
        finally:
            await self.stop()

    async def stop(self):
        """Hentikan polling dan tutup session"""
        self.is_running = False
        if self.session:
            await self.session.close()
        logger.info("Depth polling stopped")
