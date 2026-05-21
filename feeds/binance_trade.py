"""
Binance Futures Trade Stream (aggTrade) - Endpoint /market/ws
"""

import asyncio
import json
import logging
import traceback
from datetime import datetime
from typing import Callable, Optional

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class BinanceTradeStream:
    def __init__(self, symbol: str = "btcusdt", on_trade: Optional[Callable] = None):
        self.symbol = symbol.lower()
        # Gunakan endpoint yang benar: /market/ws
        self.url = f"wss://fstream.binance.com/market/ws/{self.symbol}@aggTrade"
        self.on_trade = on_trade
        self.ws = None
        self.is_running = False
        self.reconnect_delay = 3
        self.max_reconnect_delay = 30

    def _parse_trade(self, data: dict) -> dict:
        """Parse raw aggTrade message"""
        return {
            'symbol': data['s'],
            'price': float(data['p']),
            'quantity': float(data['q']),
            'side': 'SELL' if data.get('m', False) else 'BUY',  # m=True -> seller aggressive
            'trade_time': datetime.fromtimestamp(data['T'] / 1000.0),
            'agg_trade_id': data['a']
        }

    def _print_trade(self, trade: dict) -> None:
        time_str = trade['trade_time'].strftime('%H:%M:%S')
        side_color = "\033[92m" if trade['side'] == 'BUY' else "\033[91m"
        reset = "\033[0m"
        print(f"[{time_str}] {trade['symbol']} {side_color}{trade['side']}{reset} | "
              f"Price: {trade['price']:,.2f} | Qty: {trade['quantity']:.4f}")

    async def _reconnect(self) -> None:
        delay = self.reconnect_delay
        while self.is_running:
            logger.warning(f"Reconnecting in {delay}s...")
            await asyncio.sleep(delay)
            try:
                await self.connect()
                break
            except Exception as e:
                logger.error(f"Reconnect failed: {e}")
                delay = min(delay * 1.5, self.max_reconnect_delay)

    async def connect(self) -> None:
        """Membuka koneksi WebSocket ke Binance Futures (Market Stream)"""
        try:
            self.ws = await websockets.connect(self.url, ping_interval=20, ping_timeout=10)
            logger.info(f"Connected to {self.url}")
            await self._listen()
        except (ConnectionClosed, WebSocketException, OSError) as e:
            logger.error(f"Connection error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            traceback.print_exc()
            raise

    async def _listen(self) -> None:
        """Loop menerima pesan WebSocket"""
        try:
            async for message in self.ws:
                try:
                    data = json.loads(message)
                    if data.get('e') == 'aggTrade':
                        trade = self._parse_trade(data)
                        self._print_trade(trade)
                        if self.on_trade:
                            await self.on_trade(trade)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON: {message[:100]}")
                except Exception as e:
                    logger.error(f"Process error: {e}")
        except ConnectionClosed:
            logger.warning("Connection closed")
            if self.is_running:
                await self._reconnect()
        except Exception as e:
            logger.error(f"Listen loop error: {e}")
            if self.is_running:
                await self._reconnect()

    async def start(self) -> None:
        """Mulai streaming (blocking, jalankan di asyncio task)"""
        self.is_running = True
        while self.is_running:
            try:
                await self.connect()
                await asyncio.sleep(0.5)  # jeda kecil sebelum restart jika perlu
            except Exception as e:
                logger.error(f"Start loop error: {e}")
                await asyncio.sleep(self.reconnect_delay)

    async def stop(self) -> None:
        """Hentikan stream dengan graceful"""
        self.is_running = False
        if self.ws:
            await self.ws.close()
        logger.info("Trade stream stopped")