"""
AegisFlow Terminal Dashboard - Colorful & Enhanced UI
Menampilkan semua data realtime dengan warna-warna cerah, emoji, dan balance/PnL yang sangat mencolok.
"""

import asyncio
import os
import logging
from datetime import datetime
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal, Grid
from textual.widgets import Header, Footer, Static, Label
from textual.reactive import reactive
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Engine and feeds
from engine.cvd import CVDEngine
from engine.signal_engine import SignalEngine
from feeds.binance_trade import BinanceTradeStream
from feeds.binance_depth import BinanceDepthStream
from engine.imbalance import compute_obi

# Paper Trading
from paper_trading.executor import PaperTradingExecutor

# Optional storage & alerts
try:
    from storage.redis_client import RedisClient
    from storage.postgres_client import PostgresClient
    STORAGE_AVAILABLE = True
except ImportError:
    STORAGE_AVAILABLE = False
try:
    from alerts.telegram_alert import TelegramAlert
    from alerts.anomaly_detector import AnomalyDetector
    ALERTS_AVAILABLE = True
except ImportError:
    ALERTS_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ==================== Custom Widgets with Enhanced Styling ====================

class StatusBar(Static):
    ws_status = reactive("🔴 DISCONNECTED")
    depth_status = reactive("⏹️ STOPPED")
    engine_status = reactive("⏹️ STOPPED")
    alert_status = reactive("🔕 OFF")
    storage_status = reactive("💾 OFF")
    paper_status = reactive("📄 OFF")

    def render(self) -> str:
        return (
            f"[bold cyan]📡 Trade WS:[/] {self.ws_status}   "
            f"[bold cyan]📊 Depth:[/] {self.depth_status}   "
            f"[bold cyan]⚙️ CVD:[/] {self.engine_status}   "
            f"[bold magenta]🔔 Alerts:[/] {self.alert_status}   "
            f"[bold yellow]💾 Storage:[/] {self.storage_status}   "
            f"[bold green]📄 Paper:[/] {self.paper_status}"
        )

class OBIPanel(Static):
    obi_value = reactive(0.0)
    pressure = reactive("NEUTRAL")
    def render(self) -> str:
        color = "green" if self.pressure == "BULLISH" else "red" if self.pressure == "BEARISH" else "yellow"
        return (
            f"[bold cyan]📊 ORDERFLOW[/]\n"
            f"┌─────────────────┐\n"
            f"│ OBI      : [bold]{self.obi_value:+.4f}[/]     │\n"
            f"│ PRESSURE : [{color}]{self.pressure}[/] │\n"
            f"└─────────────────┘"
        )

class CVDPanel(Static):
    buy_vol = reactive(0.0)
    sell_vol = reactive(0.0)
    delta = reactive(0.0)
    cvd = reactive(0.0)
    aggression = reactive("NEUTRAL")
    def render(self) -> str:
        agg_color = "green" if "BUYERS" in self.aggression else "red" if "SELLERS" in self.aggression else "yellow"
        return (
            f"[bold cyan]📈 CVD ENGINE[/]\n"
            f"┌────────────────────────┐\n"
            f"│ BUY VOL   : {self.buy_vol:.2f}         │\n"
            f"│ SELL VOL  : {self.sell_vol:.2f}         │\n"
            f"│ DELTA     : {self.delta:+.2f}         │\n"
            f"│ CVD       : {self.cvd:+.2f}         │\n"
            f"│ AGGRESSION: [{agg_color}]{self.aggression}[/] │\n"
            f"└────────────────────────┘"
        )

class TradeSummary(Static):
    last_price = reactive(0.0)
    last_side = reactive("")
    last_time = reactive("")
    trade_count = reactive(0)
    def render(self) -> str:
        side_color = "green" if self.last_side == "BUY" else "red"
        return (
            f"[bold cyan]💰 LIVE TRADE[/]\n"
            f"┌─────────────────────────┐\n"
            f"│ Symbol    : BTCUSDT            │\n"
            f"│ Last Price: [{side_color}]{self.last_price:,.2f}[/]    │\n"
            f"│ Side      : [{side_color}]{self.last_side}[/]            │\n"
            f"│ Time      : {self.last_time}              │\n"
            f"│ Trades    : {self.trade_count}               │\n"
            f"└─────────────────────────┘"
        )

class SignalPanel(Static):
    score = reactive(0.0)
    signal = reactive("NEUTRAL")
    expansion = reactive("LOW")
    def render(self) -> str:
        if "BULLISH" in self.signal:
            col = "green"
            arrow = "🚀"
        elif "BEARISH" in self.signal:
            col = "red"
            arrow = "📉"
        else:
            col = "yellow"
            arrow = "⚖️"
        return (
            f"[bold magenta]⚡ SIGNAL ENGINE[/]\n"
            f"┌────────────────────────┐\n"
            f"│ SCORE      : [{col}]{self.score:+.4f}[/]     │\n"
            f"│ SIGNAL     : [{col}]{self.signal}[/] {arrow}   │\n"
            f"│ EXPANSION  : {self.expansion}            │\n"
            f"└────────────────────────┘"
        )

class PaperTradingPanel(Static):
    # Properti reaktif untuk update realtime
    balance = reactive(0.0)
    pnl = reactive(0.0)
    return_pct = reactive(0.0)
    position_side = reactive("")
    position_qty = reactive(0.0)
    entry_price = reactive(0.0)
    current_price = reactive(0.0)
    unrealized_pnl = reactive(0.0)

    def render(self) -> str:
        # Format balance dan PnL dengan teks tebal, warna kontras, dan border ganda
        bal_color = "green" if self.balance >= 10000 else "yellow"
        pnl_color = "green" if self.pnl >= 0 else "red"
        return_pct_color = "green" if self.return_pct >= 0 else "red"
        # Position info
        if self.position_side:
            pos_color = "green" if self.position_side == "long" else "red"
            pos_str = (
                f"│ 📌 Position : [{pos_color}]{self.position_side.upper()} {self.position_qty:.4f} BTC[/]     │\n"
                f"│    Entry    : {self.entry_price:.2f}                         │\n"
                f"│    Current  : {self.current_price:.2f}                         │\n"
                f"│    Unrealized: [{pnl_color}]{self.unrealized_pnl:+.2f}[/] USDT                 │"
            )
        else:
            pos_str = "│ 📌 Position : None                                   │"
        return (
            f"[bold green on black]💰💰 PAPER TRADING 💰💰[/]\n"
            f"╔════════════════════════════════════════════════╗\n"
            f"║ [bold]BALANCE :[/] [{bal_color}]{self.balance:,.2f}[/] USDT                          ║\n"
            f"║ [bold]TOTAL PnL:[/] [{pnl_color}]{self.pnl:+.2f}[/] USDT  ([{return_pct_color}]{self.return_pct:+.2f}%[/])            ║\n"
            f"╠════════════════════════════════════════════════╣\n"
            f"{pos_str}\n"
            f"╚════════════════════════════════════════════════╝"
        )

class SpreadPanel(Static):
    """Panel baru untuk menampilkan spread harga (best bid/ask). Diperoleh dari depth."""
    best_bid = reactive(0.0)
    best_ask = reactive(0.0)
    spread = reactive(0.0)
    spread_pct = reactive(0.0)

    def render(self) -> str:
        return (
            f"[bold cyan]💹 SPREAD INFO[/]\n"
            f"┌────────────────────────┐\n"
            f"│ Best Bid  : {self.best_bid:.2f}           │\n"
            f"│ Best Ask  : {self.best_ask:.2f}           │\n"
            f"│ Spread    : {self.spread:.2f} ({self.spread_pct:.4f}%) │\n"
            f"└────────────────────────┘"
        )

# ==================== Main App ====================
class AegisFlowDashboard(App):
    CSS = """
    Screen {
        background: $surface;
    }
    Container {
        layout: grid;
        grid-size: 3 2;
        grid-gutter: 2;
        padding: 1;
    }
    .panel {
        border: solid $primary;
        padding: 1;
        height: auto;
    }
    StatusBar {
        dock: bottom;
        height: 1;
        background: $panel;
    }
    PaperTradingPanel {
        border: double $success;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container():
            with Vertical(classes="panel"):
                yield TradeSummary(id="trade_summary")
            with Vertical(classes="panel"):
                yield OBIPanel(id="obi_panel")
            with Vertical(classes="panel"):
                yield SpreadPanel(id="spread_panel")
            with Vertical(classes="panel"):
                yield CVDPanel(id="cvd_panel")
            with Vertical(classes="panel"):
                yield SignalPanel(id="signal_panel")
            with Vertical(classes="panel"):
                yield PaperTradingPanel(id="paper_panel")
        yield Footer()
        yield StatusBar()

    async def on_mount(self) -> None:
        # Shared data
        self.latest_obi = 0.0
        self.latest_pressure = "NEUTRAL"
        self.latest_aggression = "NEUTRAL"
        self.was_disconnected = False
        self.latest_price = 0.0
        self.best_bid = 0.0
        self.best_ask = 0.0

        # Engines
        self.cvd_engine = CVDEngine(update_interval=1.0, on_update=self.on_cvd_update)
        await self.cvd_engine.start()
        self.signal_engine = SignalEngine(cvd_normalization_factor=1000.0)

        # Trade & Depth streams
        self.trade_stream = BinanceTradeStream(symbol="btcusdt", on_trade=self.on_trade)
        self.trade_task = asyncio.create_task(self.trade_stream.start())
        self.depth_stream = BinanceDepthStream(symbol="btcusdt", on_depth=self.on_depth)
        self.depth_task = asyncio.create_task(self.depth_stream.start())

        # Paper Trading
        self.paper_executor = PaperTradingExecutor()
        status = self.query_one(StatusBar)
        status.paper_status = "🟢 ACTIVE"

        # Optional storage & alerts (inisialisasi jika ada, tidak wajib)
        await self._init_storage()
        self.storage_task = asyncio.create_task(self._periodic_storage()) if STORAGE_AVAILABLE else None
        await self._init_alerts()
        self.alert_task = asyncio.create_task(self._periodic_alert_check()) if ALERTS_AVAILABLE else None

        # Periodic update for paper panel (every 2 sec)
        self.paper_update_task = asyncio.create_task(self._periodic_paper_update())

        # Update status bar
        status.ws_status = "🟢 CONNECTED"
        status.depth_status = "🟢 POLLING"
        status.engine_status = "🟢 RUNNING"
        status.alert_status = "🟢 ON" if ALERTS_AVAILABLE else "🔕 OFF"
        status.storage_status = "🟢 ON" if STORAGE_AVAILABLE else "🔴 OFF"

        logger.info("Dashboard ready with enhanced UI.")

    async def _periodic_paper_update(self):
        """Update paper panel every 2 seconds."""
        while True:
            await asyncio.sleep(2)
            try:
                stat = self.paper_executor.get_status()
                panel = self.query_one("#paper_panel", PaperTradingPanel)
                panel.balance = stat["balance"]
                panel.pnl = stat["total_pnl"]
                panel.return_pct = stat["return_pct"]
                if stat["open_position"]:
                    pos = stat["open_position"]
                    panel.position_side = pos["side"]
                    panel.position_qty = pos["quantity"]
                    panel.entry_price = pos["entry_price"]
                    panel.current_price = pos["current_price"]
                    panel.unrealized_pnl = pos["unrealized_pnl"]
                else:
                    panel.position_side = ""
                    panel.position_qty = 0.0
                    panel.entry_price = 0.0
                    panel.current_price = 0.0
                    panel.unrealized_pnl = 0.0
            except Exception as e:
                logger.error(f"Paper panel error: {e}")

    # ---------- Storage & Alerts (placeholder methods, bisa diisi sesuai kebutuhan) ----------
    async def _init_storage(self):
        if STORAGE_AVAILABLE:
            logger.info("Storage layer available (Redis + PostgreSQL)")
            # Inisialisasi nyata jika diperlukan

    async def _periodic_storage(self):
        while True:
            await asyncio.sleep(5)
            # Implementasi storage jika perlu

    async def _init_alerts(self):
        if ALERTS_AVAILABLE:
            logger.info("Alert system available (Telegram)")
            # Inisialisasi nyata

    async def _periodic_alert_check(self):
        while True:
            await asyncio.sleep(5)
            # Implementasi alert

    # ---------- Callbacks ----------
    async def on_cvd_update(self, state):
        cvd_panel = self.query_one("#cvd_panel", CVDPanel)
        cvd_panel.buy_vol = state.total_buy_volume
        cvd_panel.sell_vol = state.total_sell_volume
        cvd_panel.delta = state.net_delta
        cvd_panel.cvd = state.cumulative_delta
        cvd_panel.aggression = state.aggression
        self.latest_aggression = state.aggression

        result = self.signal_engine.update(
            obi=self.latest_obi,
            cvd=state.cumulative_delta,
            net_delta=state.net_delta,
            aggression=self.latest_aggression,
            pressure=self.latest_pressure
        )
        sig_panel = self.query_one("#signal_panel", SignalPanel)
        sig_panel.score = result.score
        sig_panel.signal = result.signal
        sig_panel.expansion = result.expansion_prob

        if hasattr(self, 'paper_executor') and self.latest_price > 0:
            await self.paper_executor.on_signal(result.signal, result.score, self.latest_price)

    async def on_trade(self, trade):
        trade_sum = self.query_one("#trade_summary", TradeSummary)
        trade_sum.last_price = trade['price']
        trade_sum.last_side = trade['side']
        trade_sum.last_time = trade['trade_time'].strftime('%H:%M:%S')
        trade_sum.trade_count += 1
        self.cvd_engine.add_trade(trade['side'], trade['quantity'])
        self.latest_price = trade['price']

    async def on_depth(self, depth):
        # Update OBI panel
        result = compute_obi(depth['bids'], depth['asks'])
        obi_panel = self.query_one("#obi_panel", OBIPanel)
        obi_panel.obi_value = result['obi']
        obi_panel.pressure = result['pressure']
        self.latest_obi = result['obi']
        self.latest_pressure = result['pressure']
        # Update spread panel
        if depth['bids'] and depth['asks']:
            self.best_bid = depth['bids'][0][0]
            self.best_ask = depth['asks'][0][0]
            spread = self.best_ask - self.best_bid
            spread_pct = (spread / self.best_bid) * 100 if self.best_bid else 0
            spread_panel = self.query_one("#spread_panel", SpreadPanel)
            spread_panel.best_bid = self.best_bid
            spread_panel.best_ask = self.best_ask
            spread_panel.spread = spread
            spread_panel.spread_pct = spread_pct

    async def on_unmount(self) -> None:
        logger.info("Shutting down...")
        await self.trade_stream.stop()
        self.trade_task.cancel()
        await self.depth_stream.stop()
        self.depth_task.cancel()
        await self.cvd_engine.stop()
        if self.storage_task:
            self.storage_task.cancel()
        if self.alert_task:
            self.alert_task.cancel()
        self.paper_update_task.cancel()
        logger.info("Dashboard shutdown complete.")