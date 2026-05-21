import pytest
from engine.signal_engine import SignalEngine

def test_normalize_cvd():
    engine = SignalEngine(cvd_normalization_factor=1000.0)
    assert engine.normalize_cvd(500) == 0.5
    assert engine.normalize_cvd(-800) == -0.8
    assert engine.normalize_cvd(2000) == 1.0   # clipped
    assert engine.normalize_cvd(-2000) == -1.0

def test_compute_score():
    engine = SignalEngine()
    score = engine.compute_score(obi=0.20, cvd=500)
    # normalized_cvd = 0.5, score = 0.6*0.2 + 0.4*0.5 = 0.12 + 0.20 = 0.32
    assert abs(score - 0.32) < 0.001

def test_classify_signal():
    engine = SignalEngine()
    assert engine.classify_signal(0.8) == "STRONG BULLISH"
    assert engine.classify_signal(0.4) == "BULLISH"
    assert engine.classify_signal(0.0) == "NEUTRAL"
    assert engine.classify_signal(-0.3) == "BEARISH"
    assert engine.classify_signal(-0.7) == "STRONG BEARISH"

def test_expansion_probability():
    engine = SignalEngine()
    # OBI tinggi, delta tinggi, searah -> HIGH
    prob = engine.expansion_probability(obi=0.35, cvd=100, net_delta=150)
    assert prob == "HIGH"
    # OBI sedang, delta sedang -> MEDIUM
    prob = engine.expansion_probability(obi=0.22, cvd=100, net_delta=60)
    assert prob == "MEDIUM"
    # OBI kecil -> LOW
    prob = engine.expansion_probability(obi=0.10, cvd=100, net_delta=30)
    assert prob == "LOW"