"""
Order Book Imbalance (OBI) calculator
Formula: OBI = (BidVolume - AskVolume) / (BidVolume + AskVolume)
Pressure classification: >0.10 bullish, <-0.10 bearish, else neutral
"""

from typing import List, Tuple, Dict

def compute_obi(bids: List[List[float]], asks: List[List[float]]) -> Dict:
    """
    Compute OBI from bids and asks lists.
    Each list element: [price, quantity]
    Returns dict with bid_volume, ask_volume, obi, pressure.
    """
    bid_volume = sum(qty for _, qty in bids)
    ask_volume = sum(qty for _, qty in asks)
    total = bid_volume + ask_volume
    if total == 0:
        obi = 0.0
    else:
        obi = (bid_volume - ask_volume) / total
    
    if obi > 0.10:
        pressure = "BULLISH"
    elif obi < -0.10:
        pressure = "BEARISH"
    else:
        pressure = "NEUTRAL"
    
    return {
        "bid_volume": bid_volume,
        "ask_volume": ask_volume,
        "obi": obi,
        "pressure": pressure
    }