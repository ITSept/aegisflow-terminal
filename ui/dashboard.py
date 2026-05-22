"""
AegisFlow Terminal Dashboard - Clean version (no storage, fixed ws error)
"""

import asyncio
import os
import sys
import logging
from datetime import datetime
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Header, Footer, Static
from textual.reactive import reactive
from dotenv import load_dotenv

load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import setup_logger
from engine.cvd import CVDEngine
from engine.signal_engine import SignalEngine
from feeds.binance_trade import BinanceTradeStream
from feeds.binance_depth import BinanceDepthStream
from engine.imbalance import compute_obi
from paper_trading.executor import PaperTradingExecutor

# Optional alerts
try:
    from alerts.telegram_alert import TelegramAlert
    from alerts.anomaly_detector import AnomalyDetector
    ALERTS_AVAILABLE = True
except ImportError:
    ALERTS_AVAILABLE = False

logger = setup_logger(__name__)


# ==================== UI Widgets (sama seperti sebelumnya) ====================
class StatusBar(Static):
    ws_status = reactive("🔴 DISCONNECTED")
    depth_status = reactive("⏹️ STOPPED")
    engine_status = reactive("⏹️ STOPPED")
    alert_status = reactive("🔕 OFF")
    paper_status = reactive("📄 OFF")

    def render(self) -> str:
        return (f"[bold cyan]📡 Trade WS:[/] {self.ws_status}   "
                f"[bold cyan]📊 Depth:[/] {self.depth_status}   "
                f"[bold cyan]⚙️ CVD:[/] {self.engine_status}   "
                f"[bold magenta]🔔 Alerts:[/] {self.alert_status}   "
                f"[bold green]📄 Paper:[/] {self.paper_status}")


class OBIPanel(Static):
    obi_value = reactive(0.0)
    pressure = reactive("NEUTRAL")
    def render(self) -> str:
        color = "green" if self.pressure == "BULLISH" else "red" if self.pressure == "BEARISH" else "yellow"
        return (f"[bold cyan]📊 ORDERFLOW[/]\n┌─────────────────┐\n"
                f"│ OBI      : [bold]{self.obi_value:+.4f}[/]     │\n"
                f"│ PRESSURE : [{color}]{self.pressure}[/] │\n└─────────────────┘")


class CVDPanel(Static):
    buy_vol = reactive(0.0)
    sell_vol = reactive(0.0)
    delta = reactive(0.0)
    cvd = reactive(0.0)
    aggression = reactive("NEUTRAL")
    def render(self) -> str:
        agg_color = "green" if "BUYERS" in self.aggression else "red" if "SELLERS" in self.aggression else "yellow"
        return (f"[bold cyan]📈 CVD ENGINE[/]\n┌────────────────────────┐\n"
                f"│ BUY VOL   : {self.buy_vol:.2f}         │\n"
                f"│ SELL VOL  : {self.sell_vol:.2f}         │\n"
                f"│ DELTA     : {self.delta:+.2f}         │\n"
                f"│ CVD       : {self.cvd:+.2f}         │\n"
                f"│ AGGRESSION: [{agg_color}]{self.aggression}[/] │\n└────────────────────────┘")


class TradeSummary(Static):
    last_price = reactive(0.0)
    last_side = reactive("")
    last_time = reactive("")
    trade_count = reactive(0)
    def render(self) -> str:
        side_color = "green" if self.last_side == "BUY" else "red"
        return (f"[bold cyan]💰 LIVE TRADE[/]\n┌─────────────────────────┐\n"
                f"│ Symbol    : BTCUSDT            │\n"
                f"│ Last Price: [{side_color}]{self.last_price:,.2f}[/]    │\n"
                f"│ Side      : [{side_color}]{self.last_side}[/]            │\n"
                f"│ Time      : {self.last_time}              │\n"
                f"│ Trades    : {self.trade_count}               │\n└─────────────────────────┘")


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
        return (f"[bold magenta]⚡ SIGNAL ENGINE[/]\n┌────────────────────────┐\n"
                f"│ SCORE      : [{col}]{self.score:+.4f}[/]     │\n"
                f"│ SIGNAL     : [{col}]{self.signal}[/] {arrow}   │\n"
                f"│ EXPANSION  : {self.expansion}            │\n└────────────────────────┘")


class SpreadPanel(Static):
    best_bid = reactive(0.0)
    best_ask = reactive(0.0)
    spread = reactive(0.0)
    spread_pct = reactive(0.0)
    def render(self) -> str:
        return (f"[bold cyan]💹 SPREAD INFO[/]\n┌────────────────────────┐\n"
                f"│ Best Bid  : {self.best_bid:.2f}           │\n"
                f"│ Best Ask  : {self.best_ask:.2f}           │\n"
                f"│ Spread    : {self.spread:.2f} ({self.spread_pct:.4f}%) │\n└────────────────────────┘")


class PaperTradingPanel(Static):
    balance = reactive(0.0)
    pnl = reactive(0.0)
    return_pct = reactive(0.0)
    position_side = reactive("")
    position_qty = reactive(0.0)
    entry_price = reactive(0.0)
    current_price = reactive(0.0)
    unrealized_pnl = reactive(0.0)

    def render(self) -> str:
        bal_color = "green" if self.balance >= 10000 else "yellow"
        pnl_color = "green" if self.pnl >= 0 else "red"
        return_pct_color = "green" if self.return_pct >= 0 else "red"
        if self.position_side:
            pos_color = "green" if self.position_side == "long" else "red"
            pos_str = (f"│ 📌 Position : [{pos_color}]{self.position_side.upper()} {self.position_qty:.4f} BTC[/]     │\n"
                       f"│    Entry    : {self.entry_price:.2f}                         │\n"
                       f"│    Current  : {self.current_price:.2f}                         │\n"
                       f"│    Unrealized: [{pnl_color}]{self.unrealized_pnl:+.2f}[/] USDT                 │")
        else:
            pos_str = "│ 📌 Position : None                                   │"
        return (f"[bold green on black]💰💰 PAPER TRADING 💰💰[/]\n"
                f"╔════════════════════════════════════════════════╗\n"
                f"║ [bold]BALANCE :[/] [{bal_color}]{self.balance:,.2f}[/] USDT                          ║\n"
                f"║ [bold]TOTAL PnL:[/] [{pnl_color}]{self.pnl:+.2f}[/] USDT  ([{return_pct_color}]{self.return_pct:+.2f}%[/])            ║\n"
                f"╠════════════════════════════════════════════════╣\n"
                f"{pos_str}\n"
                f"╚════════════════════════════════════════════════╝")


# ==================== Main App (tanpa storage) ====================
class AegisFlowDashboard(App):
    CSS = """
    Screen { background: $surface; }
    Container { layout: grid; grid-size: 3 2; grid-gutter: 2; padding: 1; }
    .panel { border: solid $primary; padding: 1; height: auto; }
    StatusBar { dock: bottom; height: 1; background: $panel; }
    PaperTradingPanel { border: double $success; }
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
        logger.info("=" * 60)
        logger.info("AegisFlow Dashboard starting up (storage disabled)")
        logger.info("=" * 60)

        # Shared data
        self.latest_obi = 0.0
        self.latest_pressure = "NEUTRAL"
        self.latest_aggression = "NEUTRAL"
        self.was_disconnected = False
        self.latest_price = 0.0
        self.best_bid = 0.0
        self.best_ask = 0.0

        # CVD Engine
        self.cvd_engine = CVDEngine(update_interval=1.0, on_update=self.on_cvd_update)
        await self.cvd_engine.start()

        # Signal Engine
        self.signal_engine = SignalEngine(cvd_normalization_factor=1000.0)

        # Trade Stream
        self.trade_stream = BinanceTradeStream(symbol="btcusdt", on_trade=self.on_trade)
        self.trade_task = asyncio.create_task(self.trade_stream.start())

        # Depth Stream
        self.depth_stream = BinanceDepthStream(symbol="btcusdt", on_depth=self.on_depth)
        self.depth_task = asyncio.create_task(self.depth_stream.start())

        # Paper Trading
        self.paper_executor = PaperTradingExecutor()
        status = self.query_one(StatusBar)
        status.paper_status = "🟢 ACTIVE"

        # Alerts (optional)
        await self._init_alerts()
        if ALERTS_AVAILABLE and self.telegram:
            self.alert_task = asyncio.create_task(self._periodic_alert_check())
            logger.info("Alert background task created")
        else:
            self.alert_task = None

        # Periodic UI updates
        self.paper_update_task = asyncio.create_task(self._periodic_paper_update())

        # Status bar final
        status.ws_status = "🟢 CONNECTING"
        status.depth_status = "🟢 POLLING"
        status.engine_status = "🟢 RUNNING"
        status.alert_status = "🟢 ON" if (ALERTS_AVAILABLE and self.telegram) else "🔕 OFF"

        logger.info("Dashboard ready (storage disabled).")

    # ---------- Periodic Tasks ----------
    async def _periodic_paper_update(self):
        """Update paper trading panel every 2 seconds."""
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
                logger.error(f"Paper panel update error: {e}", exc_info=True)

    async def _init_alerts(self):
        if not ALERTS_AVAILABLE:
            self.telegram = None
            return
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if bot_token and chat_id:
            self.telegram = TelegramAlert(bot_token, chat_id)
            await self.telegram.start()
            self.anomaly_detector = AnomalyDetector(cooldown_seconds=300)
            logger.info("Telegram alert system active")
        else:
            self.telegram = None
            logger.warning("Telegram credentials missing, alerts disabled")

    async def _periodic_alert_check(self):
        """Check anomalies every 5 seconds and send alerts."""
        logger.info("Alert check task started (every 5s)")
        while True:
            await asyncio.sleep(5)
            if not ALERTS_AVAILABLE or self.telegram is None:
                continue
            try:
                obi_panel = self.query_one("#obi_panel", OBIPanel)
                cvd_panel = self.query_one("#cvd_panel", CVDPanel)
                sig_panel = self.query_one("#signal_panel", SignalPanel)
                status_bar = self.query_one(StatusBar)

                obi = obi_panel.obi_value
                cvd = cvd_panel.cvd
                score = sig_panel.score
                expansion = sig_panel.expansion
                ws_status = status_bar.ws_status

                alerts = []
                triggered, msg = self.anomaly_detector.check_strong_bullish(score, obi, cvd)
                if triggered: alerts.append(msg)
                triggered, msg = self.anomaly_detector.check_strong_bearish(score, obi, cvd)
                if triggered: alerts.append(msg)
                triggered, msg = self.anomaly_detector.check_high_expansion(expansion)
                if triggered: alerts.append(msg)
                triggered, msg = self.anomaly_detector.check_extreme_obi(obi)
                if triggered: alerts.append(msg)
                triggered, msg = self.anomaly_detector.check_extreme_cvd(cvd)
                if triggered: alerts.append(msg)
                triggered, msg = self.anomaly_detector.check_ws_disconnected(ws_status)
                if triggered:
                    alerts.append(msg)
                    self.was_disconnected = True
                triggered, msg = self.anomaly_detector.check_engine_recovered(ws_status, self.was_disconnected)
                if triggered:
                    alerts.append(msg)
                    self.was_disconnected = False

                for alert_msg in alerts:
                    text = (f"<b>[AEGISFLOW ALERT]</b>\nSYMBOL: BTCUSDT\nALERT: {alert_msg}\n"
                            f"OBI: {obi:+.4f}\nCVD: {cvd:+.2f}\nSCORE: {score:+.4f}\n"
                            f"EXPANSION: {expansion}\nTIME: {datetime.now().strftime('%H:%M:%S')}")
                    success = await self.telegram.send_message(text)
                    if success:
                        logger.info(f"Alert sent: {alert_msg}")
                    else:
                        logger.warning(f"Alert failed: {alert_msg}")
            except Exception as e:
                logger.error(f"Alert check error: {e}", exc_info=True)

    # ---------- Engine Callbacks ----------
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
        old_signal = sig_panel.signal
        sig_panel.score = result.score
        sig_panel.signal = result.signal
        sig_panel.expansion = result.expansion_prob
        if old_signal != result.signal:
            logger.info(f"Signal changed: {old_signal} -> {result.signal} (score={result.score:.4f})")

        # Update paper trading
        if hasattr(self, 'paper_executor') and self.latest_price > 0:
            await self.paper_executor.on_signal(result.signal, result.score, self.latest_price)

        # Update status bar - FIXED: safely check connection status
        status = self.query_one(StatusBar)
        try:
            # Try to access connection status safely
            if hasattr(self.trade_stream, 'ws') and self.trade_stream.ws:
                status.ws_status = "🟢 CONNECTED"
            else:
                status.ws_status = "🔴 DISCONNECTED"
        except Exception:
            status.ws_status = "🔴 UNKNOWN"

    async def on_trade(self, trade):
        trade_sum = self.query_one("#trade_summary", TradeSummary)
        trade_sum.last_price = trade['price']
        trade_sum.last_side = trade['side']
        trade_sum.last_time = trade['trade_time'].strftime('%H:%M:%S')
        trade_sum.trade_count += 1
        self.cvd_engine.add_trade(trade['side'], trade['quantity'])
        self.latest_price = trade['price']

        if trade_sum.trade_count % 100 == 0:
            logger.info(f"Trade count: {trade_sum.trade_count}, last price: {trade['price']:.2f}")

    async def on_depth(self, depth):
        result = compute_obi(depth['bids'], depth['asks'])
        obi_panel = self.query_one("#obi_panel", OBIPanel)
        obi_panel.obi_value = result['obi']
        obi_panel.pressure = result['pressure']
        self.latest_obi = result['obi']
        self.latest_pressure = result['pressure']

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

        if abs(result['obi']) > 0.8:
            logger.info(f"Extreme OBI detected: {result['obi']:.4f} ({result['pressure']})")

    async def on_unmount(self) -> None:
        logger.info("=" * 60)
        logger.info("Shutting down AegisFlow Dashboard...")
        await self.trade_stream.stop()
        self.trade_task.cancel()
        await self.depth_stream.stop()
        self.depth_task.cancel()
        await self.cvd_engine.stop()
        if self.alert_task:
            self.alert_task.cancel()
        self.paper_update_task.cancel()
        if ALERTS_AVAILABLE and self.telegram:
            await self.telegram.stop()
        logger.info("Dashboard shutdown complete.")