# paper_trading/executor.py
"""
Paper trading executor with automatic buy/sell decisions based on signal engine.
Logs every order, balance changes, and errors.
"""

import asyncio
import logging
from typing import Optional

from paper_trading.account import VirtualAccount
from paper_trading.config import INITIAL_BALANCE_USDT, COMMISSION_RATE
from utils.logger import setup_logger

logger = setup_logger(__name__)


class PaperTradingExecutor:
    def __init__(self, initial_balance: float = INITIAL_BALANCE_USDT):
        self.account = VirtualAccount(initial_balance, COMMISSION_RATE)
        self.last_signal: Optional[str] = None
        self.last_price: float = 0.0
        self.is_in_position: bool = False
        logger.info(
            f"PaperTradingExecutor initialized: balance={initial_balance:.2f} USDT, "
            f"commission={COMMISSION_RATE*100:.2f}%"
        )

    async def on_signal(self, signal: str, score: float, price: float) -> None:
        """
        Called whenever a new signal is available.
        Implements simple strategy: buy on BULLISH/STRONG_BULLISH when flat,
        sell on BEARISH/STRONG_BEARISH when in position.
        """
        self.last_price = price
        current_signal = signal.upper()

        # Update current price for open positions (for unrealized PnL display)
        if self.account.positions:
            for pos in self.account.positions:
                pos.current_price = price

        has_position = len(self.account.positions) > 0

        # Buy signal
        if "BULLISH" in current_signal and not has_position:
            risk_ratio = 0.2  # use 20% of available balance
            quantity = (self.account.balance_usdt * risk_ratio) / price
            if quantity > 0:
                success = self.account.buy(price, quantity)
                if success:
                    self.is_in_position = True
                    logger.info(
                        f"BUY order executed: signal={current_signal}, score={score:.4f}, "
                        f"price={price:.2f}, qty={quantity:.4f}, balance={self.account.balance_usdt:.2f}"
                    )
                else:
                    logger.warning(f"BUY order failed: insufficient balance or other error")
            else:
                logger.warning(f"BUY order skipped: quantity={quantity} (too small)")

        # Sell signal (close position)
        elif "BEARISH" in current_signal and has_position:
            pos = self.account.positions[0] if self.account.positions else None
            if pos:
                qty = pos.quantity
                success = self.account.sell(price, qty)
                if success:
                    self.is_in_position = False
                    logger.info(
                        f"SELL order executed: signal={current_signal}, score={score:.4f}, "
                        f"price={price:.2f}, qty={qty:.4f}, balance={self.account.balance_usdt:.2f}, "
                        f"PnL={self.account.total_pnl:.2f}"
                    )
                else:
                    logger.warning(f"SELL order failed (no open position?)")
            else:
                logger.warning("SELL signal but no open position found")

        # Neutral: no action

    def get_status(self) -> dict:
        """Return current virtual account status."""
        status = self.account.get_status()
        logger.debug(f"Status fetched: balance={status['balance']:.2f}, PnL={status['total_pnl']:.2f}")
        return status