import pytest
from engine.cvd import CVDEngine

@pytest.mark.asyncio
async def test_cvd_buy_sell():
    engine = CVDEngine(update_interval=100)  # long interval, not used
    engine.add_trade("BUY", 100)
    assert engine.state.total_buy_volume == 100
    assert engine.state.total_sell_volume == 0
    assert engine.state.cumulative_delta == 100
    engine.add_trade("SELL", 50)
    assert engine.state.total_buy_volume == 100
    assert engine.state.total_sell_volume == 50
    assert engine.state.cumulative_delta == 50
    engine.add_trade("BUY", 30)
    assert engine.state.cumulative_delta == 80
    assert engine.state.net_delta == 80

def test_aggression():
    engine = CVDEngine()
    engine.add_trade("BUY", 100)
    engine.add_trade("BUY", 100)
    assert engine.state.aggression == "BUYERS DOMINANT"
    engine.reset()
    engine.add_trade("SELL", 200)
    assert engine.state.aggression == "SELLERS DOMINANT"