"""
AegisFlow Terminal Dashboard - Textual App
"""

from datetime import datetime
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Header, Footer, Static, Label
from textual.reactive import reactive
import asyncio

from engine.cvd import CVDEngine
from feeds.binance_trade import BinanceTradeStream
# dari feeds.binance_depth (opsional, jika ingin OBI)
# dari engine.imbalance import compute_obi

class StatusBar(Static):
    """Menampilkan status koneksi dan engine."""
    ws_status = reactive("DISCONNECTED")
    engine_status = reactive("STOPPED")

    def render(self) -> str:
        return f"WS: {self.ws_status} | CVD Engine: {self.engine_status}"

class OBIPanel(Static):
    """Panel Order Book Imbalance (jika depth stream aktif)."""
    obi_value = reactive(0.0)
    pressure = reactive("NEUTRAL")

    def render(self) -> str:
        return (
            "[bold cyan]ORDERFLOW[/]\n"
            f"OBI      : {self.obi_value:+.4f}\n"
            f"PRESSURE : {self.pressure}"
        )

class CVDPanel(Static):
    """Panel Cumulative Volume Delta."""
    buy_vol = reactive(0.0)
    sell_vol = reactive(0.0)
    delta = reactive(0.0)
    cvd = reactive(0.0)
    aggression = reactive("NEUTRAL")

    def render(self) -> str:
        return (
            "[bold cyan]CVD ENGINE[/]\n"
            f"BUY VOL   : {self.buy_vol:.2f}\n"
            f"SELL VOL  : {self.sell_vol:.2f}\n"
            f"DELTA     : {self.delta:+.2f}\n"
            f"CVD       : {self.cvd:+.2f}\n"
            f"AGGRESSION: {self.aggression}"
        )

class TradeSummary(Static):
    """Ringkasan trade terbaru."""
    last_price = reactive(0.0)
    last_side = reactive("")
    last_time = reactive("")
    trade_count = reactive(0)

    def render(self) -> str:
        side_color = "green" if self.last_side == "BUY" else "red"
        return (
            "[bold cyan]LIVE TRADE[/]\n"
            f"Symbol    : BTCUSDT\n"
            f"Last Price: [{side_color}]{self.last_price:,.2f}[/]\n"
            f"Side      : [{side_color}]{self.last_side}[/]\n"
            f"Time      : {self.last_time}\n"
            f"Trades    : {self.trade_count}"
        )

class AegisFlowDashboard(App):
    """Textual App untuk AegisFlow Terminal."""
    CSS = """
    Screen {
        background: $surface;
    }
    Container {
        layout: grid;
        grid-size: 2 2;
        grid-gutter: 1;
        padding: 1;
    }
    .panel {
        border: solid $primary;
        padding: 1;
        height: 15;
    }
    StatusBar {
        dock: bottom;
        height: 1;
        background: $panel;
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
                yield CVDPanel(id="cvd_panel")
            with Vertical(classes="panel"):
                yield Static("Alerts/Logs placeholder", id="logs")
        yield Footer()
        yield StatusBar()

    async def on_mount(self) -> None:
        """Memulai data collectors dan engine di background."""
        self.cvd_engine = CVDEngine(update_interval=1.0, on_update=self.on_cvd_update)
        await self.cvd_engine.start()

        # Trade stream dengan callback
        self.trade_stream = BinanceTradeStream(symbol="btcusdt", on_trade=self.on_trade)
        self.trade_task = asyncio.create_task(self.trade_stream.start())

        # Depth stream optional (untuk OBI) – jika ingin, aktifkan
        # self.depth_stream = BinanceDepthStream(symbol="btcusdt", on_depth=self.on_depth)
        # self.depth_task = asyncio.create_task(self.depth_stream.start())

        # Update status bar
        status = self.query_one(StatusBar)
        status.ws_status = "CONNECTED"
        status.engine_status = "RUNNING"

        # Contoh update OBI dummy (jika depth tidak dipakai, bisa set manual atau polling)
        # Untuk demo, kita beri nilai 0.0 dan neutral dulu
        obi_panel = self.query_one("#obi_panel", OBIPanel)
        obi_panel.obi_value = 0.0
        obi_panel.pressure = "NEUTRAL"

    async def on_cvd_update(self, state):
        """Callback dari CVDEngine setiap 1 detik."""
        cvd_panel = self.query_one("#cvd_panel", CVDPanel)
        cvd_panel.buy_vol = state.total_buy_volume
        cvd_panel.sell_vol = state.total_sell_volume
        cvd_panel.delta = state.net_delta
        cvd_panel.cvd = state.cumulative_delta
        cvd_panel.aggression = state.aggression

    async def on_trade(self, trade):
        """Callback setiap ada trade baru."""
        trade_sum = self.query_one("#trade_summary", TradeSummary)
        trade_sum.last_price = trade['price']
        trade_sum.last_side = trade['side']
        trade_sum.last_time = trade['trade_time'].strftime('%H:%M:%S')
        trade_sum.trade_count += 1

    async def on_depth(self, depth):
        """Callback depth (opsional) untuk OBI."""
        from engine.imbalance import compute_obi
        result = compute_obi(depth['bids'], depth['asks'])
        obi_panel = self.query_one("#obi_panel", OBIPanel)
        obi_panel.obi_value = result['obi']
        obi_panel.pressure = result['pressure']

    async def on_unmount(self) -> None:
        """Bersihkan resource saat app ditutup."""
        await self.trade_stream.stop()
        self.trade_task.cancel()
        await self.cvd_engine.stop()
        # if hasattr(self, 'depth_task'): await self.depth_stream.stop()