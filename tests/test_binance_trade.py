import pytest
import json
from feeds.binance_trade import BinanceTradeStream

def test_parse_trade_buy():
    stream = BinanceTradeStream()
    raw = {
        "e": "aggTrade",
        "E": 123456789,
        "s": "BTCUSDT",
        "a": 12345,
        "p": "67250.00",
        "q": "0.124",
        "f": 100,
        "l": 105,
        "T": 1678901234567,
        "m": False,
        "M": True
    }
    trade = stream._parse_trade(raw)
    assert trade['symbol'] == "BTCUSDT"
    assert trade['price'] == 67250.00
    assert trade['quantity'] == 0.124
    assert trade['side'] == "BUY"
    assert trade['agg_trade_id'] == 12345

def test_parse_trade_sell():
    stream = BinanceTradeStream()
    raw = {
        "e": "aggTrade",
        "s": "BTCUSDT",
        "p": "50000",
        "q": "1",
        "T": 1678901234567,
        "m": True,
        "a": 999
    }
    trade = stream._parse_trade(raw)
    assert trade['side'] == "SELL"