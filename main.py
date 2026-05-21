cat > main.py << 'EOF'
import asyncio
import sys
sys.path.insert(0, '.')
from feeds.binance_trade import BinanceTradeStream

async def main():
    print("\n=== AegisFlow Terminal - Phase 2 (Binance Trade Stream) ===")
    print("Menampilkan realtime trade untuk BTCUSDT Futures...")
    print("Tekan Ctrl+C untuk berhenti.\n")
    stream = BinanceTradeStream(symbol="btcusdt")
    task = asyncio.create_task(stream.start())
    try:
        await task
    except asyncio.CancelledError:
        pass
    finally:
        await stream.stop()
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    print("Stopped.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExited.")
EOF