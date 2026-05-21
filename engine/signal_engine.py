"""
Signal Engine - menggabungkan OBI dan CVD menjadi composite score dan klasifikasi sinyal.
Formula: Score = 0.60 * OBI + 0.40 * normalized_CVD
Normalized CVD: menggunakan running min/max atau simple tanh? Untuk sederhana, kita gunakan
clipping ke range [-1000, 1000] lalu bagi 1000 -> [-1, 1]. Alternatif: gunatan sigmoid? 
Tapi spesifikasi minta sederhana. Kita akan gunakan divisi dengan 1000 (asumsi CVD maks 1000).
Jika CVD lebih besar, score tetap di -1..1.
"""

import math
from dataclasses import dataclass
from typing import Optional

@dataclass
class SignalResult:
    obi: float
    cvd: float
    normalized_cvd: float
    score: float
    signal: str          # STRONG BULLISH, BULLISH, NEUTRAL, BEARISH, STRONG BEARISH
    expansion_prob: str  # HIGH, MEDIUM, LOW
    aggression: str      # dari CVD engine (BUYERS DOMINANT, dll)
    pressure: str        # dari OBI (BULLISH, BEARISH, NEUTRAL)

class SignalEngine:
    def __init__(self, cvd_normalization_factor: float = 1000.0):
        """
        cvd_normalization_factor: nilai CVD yang dianggap sebagai 1.0 (penuh)
        Contoh: jika factor=1000, maka CVD=1000 -> normalized=1.0, CVD=-1000 -> normalized=-1.0
        """
        self.factor = cvd_normalization_factor
        self.last_result: Optional[SignalResult] = None

    def normalize_cvd(self, cvd: float) -> float:
        """Normalisasi CVD ke range [-1, 1] dengan clipping."""
        norm = cvd / self.factor
        return max(-1.0, min(1.0, norm))

    def compute_score(self, obi: float, cvd: float) -> float:
        """Composite score = 0.6*OBI + 0.4*normalized_CVD."""
        norm_cvd = self.normalize_cvd(cvd)
        score = 0.6 * obi + 0.4 * norm_cvd
        # Clip ke [-1, 1]
        return max(-1.0, min(1.0, score))

    def classify_signal(self, score: float) -> str:
        if score > 0.60:
            return "STRONG BULLISH"
        elif score > 0.20:
            return "BULLISH"
        elif score >= -0.20:
            return "NEUTRAL"
        elif score >= -0.60:
            return "BEARISH"
        else:
            return "STRONG BEARISH"

    def expansion_probability(self, obi: float, cvd: float, net_delta: float) -> str:
        """
        Estimasi probabilitas ekspansi berdasarkan:
        - |OBI| > 0.20 (liquidity imbalance signifikan)
        - |delta| > 50 (volume aggression)
        - arah searah (OBI positif dan delta positif atau sebaliknya)
        """
        obi_abs = abs(obi)
        delta_abs = abs(net_delta)
        # Cek kesamaan arah: (obi > 0 and net_delta > 0) or (obi < 0 and net_delta < 0)
        same_direction = (obi * net_delta) > 0

        if obi_abs > 0.30 and delta_abs > 100 and same_direction:
            return "HIGH"
        elif obi_abs > 0.20 and delta_abs > 50:
            return "MEDIUM"
        else:
            return "LOW"

    def update(self, obi: float, cvd: float, net_delta: float, aggression: str, pressure: str) -> SignalResult:
        """Main entry: compute signal from latest OBI, CVD, delta, and metadata."""
        norm_cvd = self.normalize_cvd(cvd)
        score = self.compute_score(obi, cvd)
        signal = self.classify_signal(score)
        exp_prob = self.expansion_probability(obi, cvd, net_delta)
        self.last_result = SignalResult(
            obi=obi,
            cvd=cvd,
            normalized_cvd=norm_cvd,
            score=score,
            signal=signal,
            expansion_prob=exp_prob,
            aggression=aggression,
            pressure=pressure
        )
        return self.last_result