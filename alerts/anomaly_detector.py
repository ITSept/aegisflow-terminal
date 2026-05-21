"""
Simple anomaly detection for market alerts.
"""

import time
from typing import Optional, Dict

class AnomalyDetector:
    def __init__(self, cooldown_seconds: int = 300):
        """
        cooldown_seconds: waktu minimum antar alert jenis yang sama (detik)
        """
        self.cooldown = cooldown_seconds
        self.last_alert_time: Dict[str, float] = {}  # key: alert_type

    def _can_send(self, alert_type: str) -> bool:
        now = time.time()
        last = self.last_alert_time.get(alert_type, 0)
        if now - last >= self.cooldown:
            self.last_alert_time[alert_type] = now
            return True
        return False

    def check_strong_bullish(self, score: float, obi: float, cvd: float) -> tuple[bool, str]:
        if score > 0.60 and obi > 0.15 and cvd > 100:
            return self._can_send("strong_bullish"), "STRONG BULLISH"
        return False, ""

    def check_strong_bearish(self, score: float, obi: float, cvd: float) -> tuple[bool, str]:
        if score < -0.60 and obi < -0.15 and cvd < -100:
            return self._can_send("strong_bearish"), "STRONG BEARISH"
        return False, ""

    def check_high_expansion(self, expansion_prob: str) -> tuple[bool, str]:
        if expansion_prob == "HIGH":
            return self._can_send("high_expansion"), "HIGH EXPANSION PROBABILITY"
        return False, ""

    def check_extreme_obi(self, obi: float) -> tuple[bool, str]:
        if obi > 0.80:
            return self._can_send("extreme_obi_bull"), f"EXTREME OBI BULLISH ({obi:.3f})"
        elif obi < -0.80:
            return self._can_send("extreme_obi_bear"), f"EXTREME OBI BEARISH ({obi:.3f})"
        return False, ""

    def check_extreme_cvd(self, cvd: float) -> tuple[bool, str]:
        if cvd > 2000:
            return self._can_send("extreme_cvd_bull"), f"EXTREME CVD BULLISH ({cvd:.1f})"
        elif cvd < -2000:
            return self._can_send("extreme_cvd_bear"), f"EXTREME CVD BEARISH ({cvd:.1f})"
        return False, ""

    def check_ws_disconnected(self, ws_status: str) -> tuple[bool, str]:
        if ws_status == "DISCONNECTED":
            return self._can_send("ws_disconnected"), "WEBSOCKET DISCONNECTED"
        return False, ""

    def check_engine_recovered(self, ws_status: str, was_disconnected: bool) -> tuple[bool, str]:
        if was_disconnected and ws_status == "CONNECTED":
            return self._can_send("engine_recovered"), "ENGINE RECOVERED"
        return False, ""