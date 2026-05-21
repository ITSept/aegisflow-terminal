#!/usr/bin/env python3
"""
WebSocket Debugger untuk Binance Futures
Mencoba berbagai endpoint dan mencetak semua pesan raw
"""

import asyncio
import json
import websockets
from datetime import datetime
import sys

# Endpoints yang akan diuji
ENDPOINTS = [
    ("Original (ws)", "wss://fstream.binance.com/ws/btcusdt@aggTrade"),
    ("Market/ws", "wss://fstream.binance.com/market/ws/btcusdt@aggTrade"),
    ("Market/stream", "wss://fstream.binance.com/market/stream?streams=btcusdt@aggTrade"),
    ("Spot (alternative)", "wss://stream.binance.com:9443/ws/bnbusdt@trade"),
]

async def test_endpoint(name, url, timeout=30):
    """Test satu endpoint, cetak raw message selama timeout detik"""
    print(f"\n{'='*60}")
    print(f"🔍 TESTING: {name}")
    print(f"📡 URL: {url}")
    print(f"⏱️  Timeout: {timeout} detik")
    print(f"{'='*60}")
    
    try:
        async with websockets.connect(url, ping_interval=15, ping_timeout=10) as ws:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ CONNECTED")
            
            # Task untuk mengirim ping manual (opsional, tapi library sudah otomatis)
            # Kita hanya menerima pesan
            start_time = asyncio.get_event_loop().time()
            message_count = 0
            
            while True:
                try:
                    # Tunggu pesan dengan timeout
                    message = await asyncio.wait_for(ws.recv(), timeout=5)
                    message_count += 1
                    now = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                    
                    # Coba parse JSON
                    try:
                        data = json.loads(message)
                        # Tampilkan ringkasan singkat
                        if isinstance(data, dict):
                            if 'e' in data:
                                event_type = data['e']
                                print(f"[{now}] 📨 {event_type}: {message[:150]}...")
                                if event_type == 'aggTrade':
                                    print(f"   🔥 TRADE: {data['s']} {data['p']} {data['q']} (m={data.get('m')})")
                            elif 'stream' in data:
                                print(f"[{now}] 📨 Stream: {data['stream']} -> {str(data['data'])[:100]}...")
                            else:
                                print(f"[{now}] 📨 Other: {message[:150]}...")
                        else:
                            print(f"[{now}] 📨 Raw: {message[:150]}...")
                    except json.JSONDecodeError:
                        print(f"[{now}] 📨 Non-JSON: {message[:100]}")
                    
                    # Reset timeout counter jika ada data
                    start_time = asyncio.get_event_loop().time()
                    
                    if message_count >= 5:
                        print(f"✅ Sudah menerima {message_count} pesan. Endpoint ini berfungsi.")
                        # Jangan langsung break, kita lihat 2-3 pesan lagi
                        if message_count >= 10:
                            break
                            
                except asyncio.TimeoutError:
                    elapsed = asyncio.get_event_loop().time() - start_time
                    if elapsed > timeout:
                        print(f"❌ TIMEOUT: Tidak ada pesan setelah {timeout} detik.")
                        break
                    else:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏳ Menunggu data... ({elapsed:.0f}s)")
                        await asyncio.sleep(1)
                        
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ HTTP ERROR: {e}")
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")

async def main():
    print("\n🚀 AegisFlow WebSocket Debugger")
    print("📡 Mencoba beberapa endpoint Binance Futures...")
    print("💡 Tekan Ctrl+C kapan saja untuk berhenti.\n")
    
    for name, url in ENDPOINTS:
        await test_endpoint(name, url, timeout=20)
        # Jeda sebentar antar test
        await asyncio.sleep(2)
    
    print("\n🏁 Debug selesai. Kesimpulan:")
    print("- Jika ada endpoint yang menampilkan 'TRADE', itu yang berfungsi.")
    print("- Jika semua timeout, kemungkinan ada blokir jaringan atau endpoint salah.")
    print("- Jika hanya menerima ping/pong tapi tidak ada trade, mungkin perlu subscribe.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Debug dihentikan oleh user.")
