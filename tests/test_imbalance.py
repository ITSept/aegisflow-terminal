import pytest
from engine.imbalance import compute_obi

def test_obi_bullish():
    bids = [[100, 10], [99, 5]]   # total bid = 15
    asks = [[101, 5], [102, 3]]   # total ask = 8
    result = compute_obi(bids, asks)
    assert round(result["obi"], 2) == round((15-8)/(15+8), 2)  # 7/23 ≈ 0.304
    assert result["pressure"] == "BULLISH"

def test_obi_bearish():
    bids = [[100, 5], [99, 3]]
    asks = [[101, 15], [102, 5]]
    result = compute_obi(bids, asks)
    assert result["obi"] < -0.10
    assert result["pressure"] == "BEARISH"

def test_obi_neutral():
    bids = [[100, 10], [99, 10]]
    asks = [[101, 10], [102, 10]]
    result = compute_obi(bids, asks)
    assert -0.10 <= result["obi"] <= 0.10
    assert result["pressure"] == "NEUTRAL"

def test_obi_zero_volume():
    result = compute_obi([], [])
    assert result["obi"] == 0.0
    assert result["pressure"] == "NEUTRAL"