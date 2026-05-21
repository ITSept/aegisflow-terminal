import asyncio
import sys
from feeds.binance_trade import BinanceTradeStream

async def main():
    print("\n=== AegisFlow Terminal - Phase 2 (Binance Trade Stream) ===\n")
    stream = BinanceTradeStream(symbol="btcusdt")
    task = asyncio.create_task(stream.start())
    try:
        await task
    except KeyboardInterrupt:
        await stream.stop()
        print("\nShutdown.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass