# engine/signal_engine.py
"""
Signal Engine - combines OBI and CVD into composite score and classification.
Logs significant signal changes.
"""

import math
import time
import logging
from dataclasses import dataclass
from typing import Optional

try:
    from utils.logger import setup_logger
except ImportError:
    logging.basicConfig(level=logging.INFO)
    def setup_logger(name):
        return logging.getLogger(name)

logger = setup_logger(__name__)


@dataclass
class SignalResult:
    obi: float
    cvd: float
    normalized_cvd: float
    score: float
    signal: str          # STRONG BULLISH, BULLISH, NEUTRAL, BEARISH, STRONG BEARISH
    expansion_prob: str  # HIGH, MEDIUM, LOW
    aggression: str
    pressure: str


class SignalEngine:
    def __init__(self, cvd_normalization_factor: float = 1000.0, 
                 obi_weight: float = 0.6, cvd_weight: float = 0.4,
                 log_signal_changes: bool = True):
        """
        Args:
            cvd_normalization_factor: nilai CVD yang dianggap sebagai 1.0 (penuh)
            obi_weight: bobot OBI dalam composite score (default 0.6)
            cvd_weight: bobot CVD normalized (default 0.4)
            log_signal_changes: whether to log when signal classification changes
        """
        self.factor = cvd_normalization_factor
        self.obi_weight = obi_weight
        self.cvd_weight = cvd_weight
        self.log_changes = log_signal_changes
        self.last_result: Optional[SignalResult] = None
        self._last_signal = None
        logger.info(f"SignalEngine initialized: factor={self.factor}, obi_weight={obi_weight}, cvd_weight={cvd_weight}")

    def normalize_cvd(self, cvd: float) -> float:
        """Normalize CVD to range [-1, 1] with clipping."""
        norm = cvd / self.factor
        clipped = max(-1.0, min(1.0, norm))
        logger.debug(f"Normalize CVD: {cvd:.2f} -> {clipped:.4f}")
        return clipped

    def compute_score(self, obi: float, cvd: float) -> float:
        """Composite score = obi_weight * OBI + cvd_weight * normalized_CVD."""
        norm_cvd = self.normalize_cvd(cvd)
        score = self.obi_weight * obi + self.cvd_weight * norm_cvd
        score = max(-1.0, min(1.0, score))
        logger.debug(f"Score computed: obi={obi:.4f}, cvd={cvd:.2f} -> score={score:.4f}")
        return score

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
        Estimate expansion probability based on OBI magnitude, delta magnitude,
        and directional agreement.
        """
        obi_abs = abs(obi)
        delta_abs = abs(net_delta)
        same_direction = (obi * net_delta) > 0

        if obi_abs > 0.30 and delta_abs > 100 and same_direction:
            prob = "HIGH"
        elif obi_abs > 0.20 and delta_abs > 50:
            prob = "MEDIUM"
        else:
            prob = "LOW"
        logger.debug(f"Expansion prob: obi_abs={obi_abs:.3f}, delta_abs={delta_abs:.2f}, same_dir={same_direction} -> {prob}")
        return prob

    def update(self, obi: float, cvd: float, net_delta: float, aggression: str, pressure: str) -> SignalResult:
        """
        Main entry: compute signal from latest OBI, CVD, delta, and metadata.
        Returns SignalResult and logs if signal classification changed.
        """
        try:
            norm_cvd = self.normalize_cvd(cvd)
            score = self.compute_score(obi, cvd)
            signal = self.classify_signal(score)
            expansion = self.expansion_probability(obi, cvd, net_delta)

            result = SignalResult(
                obi=obi,
                cvd=cvd,
                normalized_cvd=norm_cvd,
                score=score,
                signal=signal,
                expansion_prob=expansion,
                aggression=aggression,
                pressure=pressure
            )

            # Log significant changes
            if self.log_changes:
                if self.last_result is None:
                    logger.info(f"Initial signal: {signal} (score={score:.4f}, obi={obi:+.4f}, cvd={cvd:.2f})")
                elif self.last_result.signal != signal:
                    logger.info(f"Signal changed: {self.last_result.signal} -> {signal} | "
                                f"score={score:+.4f} (was {self.last_result.score:+.4f}) | "
                                f"obi={obi:+.4f} (was {self.last_result.obi:+.4f}) | "
                                f"cvd={cvd:.2f} (was {self.last_result.cvd:.2f})")
                elif self.last_result.expansion_prob != expansion:
                    logger.info(f"Expansion probability changed: {self.last_result.expansion_prob} -> {expansion} | "
                                f"score={score:.4f}, obi={obi:+.4f}, cvd={cvd:.2f}")

            self.last_result = result
            self._last_signal = signal
            return result

        except Exception as e:
            logger.error(f"Error in signal update: {e}", exc_info=True)
            # Return a safe default
            return SignalResult(
                obi=obi, cvd=cvd, normalized_cvd=0.0, score=0.0, signal="NEUTRAL",
                expansion_prob="LOW", aggression=aggression, pressure=pressure
            )