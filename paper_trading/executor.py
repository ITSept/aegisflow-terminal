"""
Executor otomatis berdasarkan sinyal dari signal_engine.
Membeli saat sinyal BULLISH/STRONG BULLISH, menjual saat BEARISH/STRONG BEARISH.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from paper_trading.account import VirtualAccount
from paper_trading.config import INITIAL_BALANCE_USDT, COMMISSION_RATE

logger = logging.getLogger(__name__)

class PaperTradingExecutor:
    def __init__(self, initial_balance: float = INITIAL_BALANCE_USDT):
        self.account = VirtualAccount(initial_balance, COMMISSION_RATE)
        self.last_signal = None
        self.last_price = 0.0
        self.is_in_position = False

    async def on_signal(self, signal: str, score: float, price: float):
        """Dipanggil setiap ada update sinyal (bisa dari periodic check)."""
        self.last_price = price
        current_signal = signal.upper()

        # Update current price untuk posisi yang ada
        if self.account.positions:
            for pos in self.account.positions:
                pos.current_price = price

        # Cek apakah sudah punya posisi
        has_position = len(self.account.positions) > 0

        # Buy signal (Bullish atau Strong Bullish)
        if "BULLISH" in current_signal and not has_position:
            # Tentukan quantity berdasarkan risk (misal 20% dari balance)
            risk_ratio = 0.2
            quantity = (self.account.balance_usdt * risk_ratio) / price
            if quantity > 0:
                self.account.buy(price, quantity)
                self.is_in_position = True

        # Sell signal (Bearish atau Strong Bearish) – close posisi
        elif "BEARISH" in current_signal and has_position:
            # Close full position
            pos = self.account.positions[0] if self.account.positions else None
            if pos:
                self.account.sell(price, pos.quantity)
                self.is_in_position = False

        # Jika netral, tidak lakukan apa-apa

    def get_status(self) -> dict:
        """Ambil status akun virtual."""
        return self.account.get_status()