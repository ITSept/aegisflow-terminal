# engine/cvd.py
"""
Cumulative Volume Delta (CVD) Engine with comprehensive logging.
"""

import asyncio
import time
import logging
from dataclasses import dataclass, field
from typing import Optional, Callable, Awaitable

# Use centralized logger
try:
    from utils.logger import setup_logger
except ImportError:
    # Fallback if utils.logger not available
    logging.basicConfig(level=logging.INFO)
    def setup_logger(name):
        return logging.getLogger(name)

logger = setup_logger(__name__)


@dataclass
class CVDState:
    """Current state of CVD engine."""
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
    """
    Real‑time Cumulative Volume Delta calculator.
    Processes each trade, maintains state, and emits periodic updates.
    """

    def __init__(self, update_interval: float = 1.0,
                 on_update: Optional[Callable[[CVDState], Awaitable[None]]] = None):
        """
        Args:
            update_interval: Seconds between status callbacks.
            on_update: Async callback called with current state every interval.
        """
        self.state = CVDState()
        self.update_interval = update_interval
        self.on_update = on_update
        self._running = False
        self._task: Optional[asyncio.Task] = None
        logger.info(f"CVDEngine initialized: update_interval={update_interval}s")

    def add_trade(self, side: str, volume: float) -> None:
        """
        Process a single trade.
        """
        try:
            if side == "BUY":
                self.state.add_buy(volume)
                logger.debug(f"Trade BUY {volume:.4f} | CVD now {self.state.cumulative_delta:.2f}")
            elif side == "SELL":
                self.state.add_sell(volume)
                logger.debug(f"Trade SELL {volume:.4f} | CVD now {self.state.cumulative_delta:.2f}")
            else:
                raise ValueError(f"Invalid side: {side}")

            # Optional: log if delta is large (e.g., > 100)
            if abs(self.state.last_delta) > 100:
                logger.info(f"Large delta detected: {self.state.last_delta:+.2f} (CVD: {self.state.cumulative_delta:.2f})")
        except Exception as e:
            logger.error(f"Error in add_trade side={side} volume={volume}: {e}", exc_info=True)

    async def _periodic_report(self) -> None:
        """Background task that calls callback or prints status at regular intervals."""
        logger.info("Periodic reporting task started")
        while self._running:
            await asyncio.sleep(self.update_interval)
            try:
                if self.on_update:
                    await self.on_update(self.state)
                else:
                    self._print_status()
            except Exception as e:
                logger.error(f"Error in periodic report: {e}", exc_info=True)

    def _print_status(self) -> None:
        """Default console output if no callback is provided."""
        timestamp = time.strftime("%H:%M:%S")
        print(f"\n[CVD @ {timestamp}]")
        print(f"  Buy Volume  : {self.state.total_buy_volume:.2f}")
        print(f"  Sell Volume : {self.state.total_sell_volume:.2f}")
        print(f"  Delta       : {self.state.net_delta:+.2f}")
        print(f"  CVD         : {self.state.cumulative_delta:+.2f}")
        print(f"  Aggression  : {self.state.aggression}")
        print("-" * 40)

    async def start(self) -> None:
        """Start the CVD engine background task."""
        if self._running:
            logger.warning("CVDEngine already running")
            return
        self._running = True
        self._task = asyncio.create_task(self._periodic_report())
        logger.info("CVDEngine started")

    async def stop(self) -> None:
        """Stop the CVD engine gracefully."""
        if not self._running:
            logger.warning("CVDEngine already stopped")
            return
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info(f"CVDEngine stopped. Final stats: Buy={self.state.total_buy_volume:.2f}, Sell={self.state.total_sell_volume:.2f}, CVD={self.state.cumulative_delta:.2f}")

    def reset(self) -> None:
        """Reset all counters to zero."""
        self.state = CVDState()
        logger.info("CVDEngine reset")