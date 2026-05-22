# feeds/binance_trade.py
"""
Binance Futures Trade Stream (aggTrade) with logging and proper ws attribute.
"""

import asyncio
import json
import logging
import traceback
from datetime import datetime
from typing import Callable, Optional

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

# Use centralized logger if available, else fallback
try:
    from utils.logger import setup_logger
except ImportError:
    def setup_logger(name):
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(name)

logger = setup_logger(__name__)


class BinanceTradeStream:
    def __init__(self, symbol: str = "btcusdt", on_trade: Optional[Callable] = None):
        self.symbol = symbol.lower()
        self.stream_name = f"{self.symbol}@aggTrade"
        self.url = f"wss://fstream.binance.com/market/ws/{self.stream_name}"
        self.on_trade = on_trade
        self.ws = None
        self.is_running = False
        self.reconnect_delay = 3
        self.max_reconnect_delay = 30
        logger.info(f"Trade stream initialized for {self.symbol} (endpoint: {self.url})")

    def _parse_trade(self, data: dict) -> dict:
        return {
            'symbol': data['s'],
            'price': float(data['p']),
            'quantity': float(data['q']),
            'side': 'SELL' if data.get('m', False) else 'BUY',
            'trade_time': datetime.fromtimestamp(data['T'] / 1000.0),
            'agg_trade_id': data['a']
        }

    def _print_trade(self, trade: dict) -> None:
        time_str = trade['trade_time'].strftime('%H:%M:%S')
        side_color = "\033[92m" if trade['side'] == 'BUY' else "\033[91m"
        reset_color = "\033[0m"
        print(f"[{time_str}] {trade['symbol']} {side_color}{trade['side']}{reset_color} | "
              f"Price: {trade['price']:,.2f} | Qty: {trade['quantity']:.4f}")

    async def _reconnect(self) -> None:
        delay = self.reconnect_delay
        while self.is_running:
            logger.warning(f"Trade reconnect in {delay}s...")
            await asyncio.sleep(delay)
            try:
                await self.connect()
                break
            except Exception as e:
                logger.error(f"Trade reconnect failed: {e}")
                delay = min(delay * 1.5, self.max_reconnect_delay)

    async def connect(self) -> None:
        try:
            self.ws = await websockets.connect(self.url, ping_interval=20, ping_timeout=10)
            logger.info(f"Connected to {self.url}")
            await self._listen()
        except (ConnectionClosed, WebSocketException, OSError) as e:
            logger.error(f"Trade connection error: {e}")
            raise
        except Exception as e:
            logger.error(f"Trade unexpected error: {e}", exc_info=True)
            raise

    async def _listen(self) -> None:
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
                    logger.error(f"Trade invalid JSON: {message[:100]}")
                except Exception as e:
                    logger.error(f"Trade process error: {e}")
        except ConnectionClosed:
            logger.warning("Trade WebSocket connection closed")
            if self.is_running:
                await self._reconnect()
        except Exception as e:
            logger.error(f"Trade listen error: {e}", exc_info=True)
            if self.is_running:
                await self._reconnect()

    async def start(self) -> None:
        self.is_running = True
        logger.info("Trade stream starting...")
        while self.is_running:
            try:
                await self.connect()
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Trade start loop error: {e}")
                await asyncio.sleep(self.reconnect_delay)

    async def stop(self) -> None:
        self.is_running = False
        if self.ws:
            await self.ws.close()
        logger.info("Trade stream stopped")

    @property
    def is_connected(self) -> bool:
        """Return True if websocket is active and open."""
        return self.ws is not None and not self.ws.closed