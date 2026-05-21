"""
Virtual account untuk paper trading.
Menyimpan saldo, posisi, dan riwayat order.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class Position:
    symbol: str
    side: str          # "long" atau "short"
    entry_price: float
    quantity: float
    timestamp: datetime
    current_price: float = 0.0

@dataclass
class Order:
    symbol: str
    side: str          # "buy" atau "sell"
    price: float
    quantity: float
    timestamp: datetime
    status: str = "filled"  # filled, cancelled

class VirtualAccount:
    def __init__(self, initial_balance: float = 10000.0, commission_rate: float = 0.0004):
        self.balance_usdt = initial_balance
        self.initial_balance = initial_balance
        self.commission_rate = commission_rate
        self.positions: List[Position] = []   # hanya support long untuk sederhana
        self.order_history: List[Order] = []
        self.total_pnl = 0.0

    def buy(self, price: float, quantity: float, symbol: str = "BTCUSDT") -> bool:
        """Buy long (virtual)."""
        cost = price * quantity
        commission = cost * self.commission_rate
        total_cost = cost + commission
        if total_cost > self.balance_usdt:
            logger.warning(f"Insufficient balance: need {total_cost:.2f} USDT, have {self.balance_usdt:.2f}")
            return False
        self.balance_usdt -= total_cost
        # Open position
        pos = Position(
            symbol=symbol,
            side="long",
            entry_price=price,
            quantity=quantity,
            timestamp=datetime.now()
        )
        self.positions.append(pos)
        order = Order(symbol=symbol, side="buy", price=price, quantity=quantity, timestamp=datetime.now())
        self.order_history.append(order)
        logger.info(f"BUY {quantity} {symbol} @ {price:.2f} | Cost: {cost:.2f} | Commission: {commission:.2f} | Balance: {self.balance_usdt:.2f}")
        return True

    def sell(self, price: float, quantity: float = None, symbol: str = "BTCUSDT") -> bool:
        """Sell long position (close or partial)."""
        # Cari posisi long
        pos = next((p for p in self.positions if p.symbol == symbol and p.side == "long"), None)
        if not pos:
            logger.warning("No open long position to sell")
            return False
        if quantity is None or quantity > pos.quantity:
            quantity = pos.quantity
        # Hitung revenue
        revenue = price * quantity
        commission = revenue * self.commission_rate
        net_revenue = revenue - commission
        self.balance_usdt += net_revenue
        # Hitung PnL
        pnl = (price - pos.entry_price) * quantity
        self.total_pnl += pnl
        # Update posisi
        pos.quantity -= quantity
        if pos.quantity <= 0:
            self.positions.remove(pos)
        order = Order(symbol=symbol, side="sell", price=price, quantity=quantity, timestamp=datetime.now())
        self.order_history.append(order)
        logger.info(f"SELL {quantity} {symbol} @ {price:.2f} | Revenue: {revenue:.2f} | Commission: {commission:.2f} | PnL: {pnl:.2f} | Balance: {self.balance_usdt:.2f}")
        return True

    def get_status(self) -> dict:
        """Ringkasan akun virtual."""
        position = self.positions[0] if self.positions else None
        # Update current price untuk posisi (asumsikan sudah di-set dari luar)
        return {
            "balance": self.balance_usdt,
            "initial_balance": self.initial_balance,
            "total_pnl": self.total_pnl,
            "return_pct": ((self.balance_usdt + (position.quantity * position.current_price if position else 0) - self.initial_balance) / self.initial_balance) * 100 if self.initial_balance else 0,
            "open_position": {
                "side": position.side if position else None,
                "quantity": position.quantity if position else 0,
                "entry_price": position.entry_price if position else 0,
                "current_price": position.current_price if position else 0,
                "unrealized_pnl": ((position.current_price - position.entry_price) * position.quantity) if position else 0
            } if position else None
        }