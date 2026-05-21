"""
AegisFlow Terminal Dashboard - Phase 8 Complete
Integrates: Trade Stream, Depth Stream, CVD Engine, Signal Engine,
            Storage (Redis + PostgreSQL), Alert System (Telegram),
            Paper Trading (Virtual), and Textual UI.
"""

import asyncio
import os
import logging
from datetime import datetime
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Header, Footer, Static
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

# Storage (optional)
try:
    from storage.redis_client import RedisClient
    from storage.postgres_client import PostgresClient
    STORAGE_AVAILABLE = True
except ImportError:
    STORAGE_AVAILABLE = False
    logging.warning("Storage modules not available. Disabling persistence.")

# Alerts (optional)
try:
    from alerts.telegram_alert import TelegramAlert
    from alerts.anomaly_detector import AnomalyDetector
    ALERTS_AVAILABLE = True
except ImportError:
    ALERTS_AVAILABLE = False
    logging.warning("Alert modules not available. Disabling Telegram alerts.")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ==================== UI Widgets ====================
class StatusBar(Static):
    ws_status = reactive("DISCONNECTED")
    depth_status = reactive("STOPPED")
    engine_status = reactive("STOPPED")
    alert_status = reactive("OFF")
    storage_status = reactive("OFF")
    paper_status = reactive("OFF")

    def render(self) -> str:
        return (f"Trade WS: {self.ws_status} | Depth: {self.depth_status} | "
                f"CVD: {self.engine_status} | Alerts: {self.alert_status} | "
                f"Storage: {self.storage_status} | Paper: {self.paper_status}")

class OBIPanel(Static):
    obi_value = reactive(0.0)
    pressure = reactive("NEUTRAL")
    def render(self) -> str:
        return (f"[bold cyan]ORDERFLOW[/]\nOBI      : {self.obi_value:+.4f}\n"
                f"PRESSURE : {self.pressure}")

class CVDPanel(Static):
    buy_vol = reactive(0.0)
    sell_vol = reactive(0.0)
    delta = reactive(0.0)
    cvd = reactive(0.0)
    aggression = reactive("NEUTRAL")
    def render(self) -> str:
        return (f"[bold cyan]CVD ENGINE[/]\nBUY VOL   : {self.buy_vol:.2f}\n"
                f"SELL VOL  : {self.sell_vol:.2f}\nDELTA     : {self.delta:+.2f}\n"
                f"CVD       : {self.cvd:+.2f}\nAGGRESSION: {self.aggression}")

class TradeSummary(Static):
    last_price = reactive(0.0)
    last_side = reactive("")
    last_time = reactive("")
    trade_count = reactive(0)
    def render(self) -> str:
        side_color = "green" if self.last_side == "BUY" else "red"
        return (f"[bold cyan]LIVE TRADE[/]\nSymbol    : BTCUSDT\n"
                f"Last Price: [{side_color}]{self.last_price:,.2f}[/]\n"
                f"Side      : [{side_color}]{self.last_side}[/]\n"
                f"Time      : {self.last_time}\nTrades    : {self.trade_count}")

class SignalPanel(Static):
    score = reactive(0.0)
    signal = reactive("NEUTRAL")
    expansion = reactive("LOW")
    def render(self) -> str:
        if "BULLISH" in self.signal:
            col = "green"
        elif "BEARISH" in self.signal:
            col = "red"
        else:
            col = "yellow"
        return (f"[bold magenta]⚡ SIGNAL ENGINE[/]\nSCORE      : [{col}]{self.score:+.4f}[/]\n"
                f"SIGNAL     : [{col}]{self.signal}[/]\nEXPANSION  : {self.expansion}")

class PaperTradingPanel(Static):
    balance = reactive(0.0)
    pnl = reactive(0.0)
    return_pct = reactive(0.0)
    position_side = reactive("")
    position_qty = reactive(0.0)
    unrealized_pnl = reactive(0.0)
    entry_price = reactive(0.0)
    current_price = reactive(0.0)

    def render(self) -> str:
        pos_str = ""
        if self.position_side:
            pos_str = (f"Position  : {self.position_side.upper()} {self.position_qty:.4f} BTC\n"
                       f"Entry     : {self.entry_price:.2f}\n"
                       f"Current   : {self.current_price:.2f}\n"
                       f"Unrealized: {self.unrealized_pnl:+.2f} USDT\n")
        else:
            pos_str = "Position  : None\n"
        return (f"[bold green]💰 PAPER TRADING[/]\n"
                f"Balance   : {self.balance:.2f} USDT\n"
                f"Total PnL : {self.pnl:+.2f} USDT ({self.return_pct:+.2f}%)\n"
                f"{pos_str}")

# ==================== Main App ====================
class AegisFlowDashboard(App):
    CSS = """
    Screen { background: $surface; }
    Container { layout: grid; grid-size: 2 2; grid-gutter: 1; padding: 1; }
    .panel { border: solid $primary; padding: 1; height: 18; }
    StatusBar { dock: bottom; height: 1; background: $panel; }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container():
            with Vertical(classes="panel"):
                yield TradeSummary(id="trade_summary")
            with Vertical(classes="panel"):
                yield OBIPanel(id="obi_panel")
            with Vertical(classes="panel"):
                yield SignalPanel(id="signal_panel")
            with Vertical(classes="panel"):
                yield CVDPanel(id="cvd_panel")
            with Vertical(classes="panel"):
                yield PaperTradingPanel(id="paper_panel")
        yield Footer()
        yield StatusBar()

    async def on_mount(self) -> None:
        # --- Shared data ---
        self.latest_obi = 0.0
        self.latest_pressure = "NEUTRAL"
        self.latest_aggression = "NEUTRAL"
        self.was_disconnected = False
        self.latest_price = 0.0

        # --- CVD Engine (with periodic callback) ---
        self.cvd_engine = CVDEngine(update_interval=1.0, on_update=self.on_cvd_update)
        await self.cvd_engine.start()

        # --- Signal Engine ---
        self.signal_engine = SignalEngine(cvd_normalization_factor=1000.0)

        # --- Trade Stream ---
        self.trade_stream = BinanceTradeStream(symbol="btcusdt", on_trade=self.on_trade)
        self.trade_task = asyncio.create_task(self.trade_stream.start())

        # --- Depth Stream for OBI ---
        self.depth_stream = BinanceDepthStream(symbol="btcusdt", on_depth=self.on_depth)
        self.depth_task = asyncio.create_task(self.depth_stream.start())

        # --- Paper Trading Executor ---
        self.paper_executor = PaperTradingExecutor()
        # Update status bar paper status
        status = self.query_one(StatusBar)
        status.paper_status = "ACTIVE"

        # --- Storage (Redis + PostgreSQL) ---
        await self._init_storage()
        self.storage_task = asyncio.create_task(self._periodic_storage())

        # --- Alert System (Telegram + Anomaly Detection) ---
        await self._init_alerts()
        self.alert_task = asyncio.create_task(self._periodic_alert_check())

        # --- Periodic update for Paper Trading Panel (every 2 seconds) ---
        self.paper_update_task = asyncio.create_task(self._periodic_paper_update())

        # --- Update status bar initial state ---
        status.ws_status = "CONNECTING"
        status.depth_status = "POLLING"
        status.engine_status = "RUNNING"
        status.alert_status = "ON" if ALERTS_AVAILABLE and self.telegram else "OFF"
        status.storage_status = "ON" if STORAGE_AVAILABLE and self.pg_client else "OFF"

        logger.info("Dashboard fully initialized with Paper Trading.")

    # ---------- Periodic Paper Trading Panel Update ----------
    async def _periodic_paper_update(self):
        """Update paper trading panel every 2 seconds."""
        while True:
            await asyncio.sleep(2)
            try:
                status = self.paper_executor.get_status()
                panel = self.query_one("#paper_panel", PaperTradingPanel)
                panel.balance = status["balance"]
                panel.pnl = status["total_pnl"]
                panel.return_pct = status["return_pct"]
                if status["open_position"]:
                    pos = status["open_position"]
                    panel.position_side = pos["side"] if pos["side"] else ""
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
                logger.error(f"Paper panel update error: {e}")

    # ---------- Storage Integration ----------
    async def _init_storage(self):
        if not STORAGE_AVAILABLE:
            self.redis_client = None
            self.pg_client = None
            return
        try:
            self.redis_client = RedisClient(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", 6379)),
                db=int(os.getenv("REDIS_DB", 0)),
                password=os.getenv("REDIS_PASSWORD", None)
            )
            await self.redis_client.connect()
            pg_dsn = (f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
                      f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}")
            self.pg_client = PostgresClient(pg_dsn)
            await self.pg_client.connect()
            await self.pg_client.init_schema()
            logger.info("Storage layer ready")
        except Exception as e:
            logger.error(f"Storage init failed: {e}")
            self.redis_client = None
            self.pg_client = None

    async def _periodic_storage(self):
        """Save snapshot every 5 seconds if storage available."""
        while True:
            await asyncio.sleep(5)
            if not STORAGE_AVAILABLE or self.pg_client is None:
                continue
            try:
                obi_panel = self.query_one("#obi_panel", OBIPanel)
                cvd_panel = self.query_one("#cvd_panel", CVDPanel)
                sig_panel = self.query_one("#signal_panel", SignalPanel)
                await self.pg_client.insert_signal(
                    obi_panel.obi_value, cvd_panel.cvd, sig_panel.score,
                    sig_panel.signal, sig_panel.expansion,
                    cvd_panel.aggression, obi_panel.pressure
                )
                await self.pg_client.insert_obi_snapshot(obi_panel.obi_value, obi_panel.pressure)
                await self.pg_client.insert_cvd_snapshot(
                    cvd_panel.buy_vol, cvd_panel.sell_vol, cvd_panel.delta,
                    cvd_panel.cvd, cvd_panel.aggression
                )
                if self.redis_client:
                    await self.redis_client.set_latest("market_state", {
                        "timestamp": datetime.now().isoformat(),
                        "obi": obi_panel.obi_value,
                        "pressure": obi_panel.pressure,
                        "cvd": cvd_panel.cvd,
                        "aggression": cvd_panel.aggression,
                        "score": sig_panel.score,
                        "signal": sig_panel.signal,
                        "expansion": sig_panel.expansion
                    }, expire=3600)
                logger.debug("Storage snapshot saved")
            except Exception as e:
                logger.error(f"Storage error: {e}")

    # ---------- Alert Integration ----------
    async def _init_alerts(self):
        if not ALERTS_AVAILABLE:
            self.telegram = None
            self.anomaly_detector = None
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
                    await self.telegram.send_message(text)
            except Exception as e:
                logger.error(f"Alert check error: {e}")

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
        sig_panel.score = result.score
        sig_panel.signal = result.signal
        sig_panel.expansion = result.expansion_prob

        # Update paper trading with signal and latest price
        if hasattr(self, 'paper_executor') and self.latest_price > 0:
            await self.paper_executor.on_signal(result.signal, result.score, self.latest_price)

        status = self.query_one(StatusBar)
        status.ws_status = "CONNECTED" if self.trade_stream.ws else "CONNECTING"

    async def on_trade(self, trade):
        trade_sum = self.query_one("#trade_summary", TradeSummary)
        trade_sum.last_price = trade['price']
        trade_sum.last_side = trade['side']
        trade_sum.last_time = trade['trade_time'].strftime('%H:%M:%S')
        trade_sum.trade_count += 1
        self.cvd_engine.add_trade(trade['side'], trade['quantity'])
        self.latest_price = trade['price']

    async def on_depth(self, depth):
        result = compute_obi(depth['bids'], depth['asks'])
        obi_panel = self.query_one("#obi_panel", OBIPanel)
        obi_panel.obi_value = result['obi']
        obi_panel.pressure = result['pressure']
        self.latest_obi = result['obi']
        self.latest_pressure = result['pressure']

    # ---------- Cleanup ----------
    async def on_unmount(self) -> None:
        logger.info("Shutting down dashboard...")
        await self.trade_stream.stop()
        self.trade_task.cancel()
        await self.depth_stream.stop()
        self.depth_task.cancel()
        await self.cvd_engine.stop()
        for task in [self.storage_task, self.alert_task, self.paper_update_task]:
            if task:
                task.cancel()
        if STORAGE_AVAILABLE and self.pg_client:
            await self.pg_client.close()
        if STORAGE_AVAILABLE and self.redis_client:
            await self.redis_client.close()
        if ALERTS_AVAILABLE and self.telegram:
            await self.telegram.stop()
        logger.info("Dashboard shutdown complete.")