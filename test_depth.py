import asyncio
import json
import websockets

async def test_depth(url):
    print(f"Connecting to {url}")
    try:
        async with websockets.connect(url, ping_interval=20, ping_timeout=10) as ws:
            print("Connected! Waiting for depth data...")
            for i in range(5):
                msg = await asyncio.wait_for(ws.recv(), timeout=10)
                data = json.loads(msg)
                bids = len(data.get('bids', []))
                asks = len(data.get('asks', []))
                print(f"Update {i+1}: bids={bids}, asks={asks}")
                if bids > 0:
                    print(f"  Top bid: {data['bids'][0]}")
                if asks > 0:
                    print(f"  Top ask: {data['asks'][0]}")
            print("Test selesai.")
    except Exception as e:
        print(f"Error: {e}")

async def main():
    endpoints = [
        "wss://fstream.binance.com/market/ws/btcusdt@depth20",
        "wss://fstream.binance.com/market/ws/btcusdt@depth20@100ms",
        "wss://fstream.binance.com/ws/btcusdt@depth20",
        "wss://fstream.binance.com/ws/btcusdt@depth20@100ms",
    ]
    for url in endpoints:
        print("\n" + "="*60)
        await test_depth(url)
        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())
