cat > feeds/binance_trade.py << 'EOF'
import asyncio
import json
import logging
from datetime import datetime
from typing import Callable, Optional
import websockets
from websockets.exceptions import ConnectionClosed

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class BinanceTradeStream:
    def __init__(self, symbol: str = "btcusdt", on_trade: Optional[Callable] = None):
        self.symbol = symbol.lower()
        self.stream_name = f"{self.symbol}@aggTrade"
        self.url = f"wss://fstream.binance.com/ws/{self.stream_name}"
        self.on_trade = on_trade
        self.ws = None
        self.is_running = False
        self.reconnect_delay = 3
        self.max_reconnect_delay = 30

    async def connect(self):
        try:
            self.ws = await websockets.connect(self.url)
            logger.info(f"Connected to {self.url}")
            await self._listen()
        except Exception as e:
            logger.error(f"Connection error: {e}")
            raise

    async def _listen(self):
        try:
            async for message in self.ws:
                data = json.loads(message)
                if data.get('e') == 'aggTrade':
                    trade = {
                        'symbol': data['s'],
                        'price': float(data['p']),
                        'quantity': float(data['q']),
                        'side': 'SELL' if data.get('m', False) else 'BUY',
                        'trade_time': datetime.fromtimestamp(data['T'] / 1000.0)
                    }
                    self._print_trade(trade)
                    if self.on_trade:
                        await self.on_trade(trade)
        except ConnectionClosed:
            logger.warning("Connection closed")
            if self.is_running:
                await self._reconnect()
        except Exception as e:
            logger.error(f"Listen error: {e}")
            if self.is_running:
                await self._reconnect()

    async def _reconnect(self):
        delay = self.reconnect_delay
        while self.is_running:
            logger.warning(f"Reconnecting in {delay}s...")
            await asyncio.sleep(delay)
            try:
                await self.connect()
                break
            except Exception:
                delay = min(delay * 1.5, self.max_reconnect_delay)

    def _print_trade(self, trade):
        time_str = trade['trade_time'].strftime('%H:%M:%S')
        side_color = "\033[92m" if trade['side'] == 'BUY' else "\033[91m"
        reset = "\033[0m"
        print(f"[{time_str}] {trade['symbol']} {side_color}{trade['side']}{reset} | Price: {trade['price']:,.2f} | Qty: {trade['quantity']:.4f}")

    async def start(self):
        self.is_running = True
        while self.is_running:
            try:
                await self.connect()
            except Exception:
                await asyncio.sleep(self.reconnect_delay)

    async def stop(self):
        self.is_running = False
        if self.ws:
            await self.ws.close()
        logger.info("Stream stopped")
EOF