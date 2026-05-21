import asyncio
import json
import websockets

async def main():
    url = "wss://fstream.binance.com/ws"
    async with websockets.connect(url) as ws:
        # Subscribe ke depth20 stream
        sub_msg = {
            "method": "SUBSCRIBE",
            "params": ["btcusdt@depth20"],
            "id": 1
        }
        await ws.send(json.dumps(sub_msg))
        print("Sent subscribe:", sub_msg)
        # Terima response subscribe
        resp = await asyncio.wait_for(ws.recv(), timeout=5)
        print("Subscribe response:", resp)
        # Sekarang tunggu depth updates
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
        print("Selesai")

asyncio.run(main())
