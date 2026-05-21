import asyncio
import json
import logging
from datetime import datetime
from typing import Callable, Optional
import websockets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BinanceTradeStream:
    def __init__(self, symbol: str = "btcusdt", on_trade: Optional[Callable] = None):
        self.symbol = symbol.lower()
        self.url = f"wss://fstream.binance.com/ws/{self.symbol}@aggTrade"
        self.on_trade = on_trade
        self.ws = None
        self.is_running = False

    async def connect(self):
        self.ws = await websockets.connect(self.url)
        logger.info(f"Connected to {self.url}")
        await self._listen()

    async def _listen(self):
        try:
            async for msg in self.ws:
                data = json.loads(msg)
                if data.get('e') == 'aggTrade':
                    trade = {
                        'symbol': data['s'],
                        'price': float(data['p']),
                        'quantity': float(data['q']),
                        'side': 'SELL' if data.get('m') else 'BUY',
                        'trade_time': datetime.fromtimestamp(data['T']/1000)
                    }
                    self._print_trade(trade)
                    if self.on_trade:
                        await self.on_trade(trade)
        except Exception as e:
            logger.error(f"Listen error: {e}")
            if self.is_running:
                await self._reconnect()

    async def _reconnect(self):
        # sederhana, tunggu 5 detik lalu connect ulang
        await asyncio.sleep(5)
        if self.is_running:
            await self.connect()

    def _print_trade(self, trade):
        time_str = trade['trade_time'].strftime('%H:%M:%S')
        side_color = '\033[92m' if trade['side'] == 'BUY' else '\033[91m'
        print(f"[{time_str}] {trade['symbol']} {side_color}{trade['side']}\033[0m | "
              f"Price: {trade['price']:,.2f} | Qty: {trade['quantity']:.4f}")

    async def start(self):
        self.is_running = True
        await self.connect()

    async def stop(self):
        self.is_running = False
        if self.ws:
            await self.ws.close()