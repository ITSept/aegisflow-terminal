"""
Cumulative Volume Delta (CVD) Engine
- Real-time aggregation of buy/sell volume
- Calculates delta and cumulative delta
- Periodic status reporting
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional, Callable, Awaitable


@dataclass
class CVDState:
    total_buy_volume: float = 0.0
    total_sell_volume: float = 0.0
    cumulative_delta: float = 0.0
    last_delta: float = 0.0
    trade_count: int = 0
    start_time: float = field(default_factory=time.time)
    last_update_time: float = field(default_factory=time.time)

    @property
    def net_delta(self) -> float:
        return self.total_buy_volume - self.total_sell_volume

    @property
    def aggression(self) -> str:
        if self.cumulative_delta > 50:
            return "BUYERS DOMINANT"
        elif self.cumulative_delta < -50:
            return "SELLERS DOMINANT"
        else:
            return "NEUTRAL"

    def add_buy(self, volume: float):
        self.total_buy_volume += volume
        self.last_delta = volume
        self.cumulative_delta += volume
        self.trade_count += 1
        self.last_update_time = time.time()

    def add_sell(self, volume: float):
        self.total_sell_volume += volume
        self.last_delta = -volume
        self.cumulative_delta -= volume
        self.trade_count += 1
        self.last_update_time = time.time()


class CVDEngine:
    def __init__(self, update_interval: float = 1.0, on_update: Optional[Callable[[CVDState], Awaitable[None]]] = None):
        self.state = CVDState()
        self.update_interval = update_interval
        self.on_update = on_update
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def add_trade(self, side: str, volume: float):
        """Fast, non-blocking trade processing."""
        if side == "BUY":
            self.state.add_buy(volume)
        elif side == "SELL":
            self.state.add_sell(volume)
        else:
            raise ValueError(f"Invalid side: {side}")

    async def _periodic_report(self):
        while self._running:
            await asyncio.sleep(self.update_interval)
            if self.on_update:
                await self.on_update(self.state)
            else:
                self._print_status()

    def _print_status(self):
        timestamp = time.strftime("%H:%M:%S")
        print(f"\n[CVD @ {timestamp}]")
        print(f"  Buy Volume  : {self.state.total_buy_volume:.2f}")
        print(f"  Sell Volume : {self.state.total_sell_volume:.2f}")
        print(f"  Delta       : {self.state.net_delta:+.2f}")
        print(f"  CVD         : {self.state.cumulative_delta:+.2f}")
        print(f"  Aggression  : {self.state.aggression}")
        print("-" * 40)

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._periodic_report())

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    def reset(self):
        self.state = CVDState()