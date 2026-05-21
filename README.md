# AegisFlow Terminal

**Real-time cryptocurrency order flow intelligence terminal** for Binance Futures (BTCUSDT).  
Built with Python, asyncio, Textual, and modern web technologies.

## Features

- ✅ **Live Trade Stream** – WebSocket connection to `aggTrade` (real trades)
- ✅ **Order Book Imbalance (OBI)** – Liquidity pressure from top 20 bid/ask levels (REST polling fallback)
- ✅ **Cumulative Volume Delta (CVD)** – Tracks buyer vs seller aggression
- ✅ **Signal Engine** – Composite score (60% OBI + 40% normalized CVD) with 5‑level classification & expansion probability
- ✅ **Rich Terminal UI** – Built with Textual, responsive and real‑time
- ✅ **Storage Layer** (optional) – Redis cache + PostgreSQL history
- ✅ **Telegram Alerts** (optional) – Instant notifications for strong signals, extreme OBI/CVD, disconnection
- ✅ **Paper Trading** (optional) – Virtual account to test strategies based on signals
- ✅ **Auto‑reconnect** – Handles network interruptions gracefully
- ✅ **Low latency & low memory** – Pure asyncio, no thread blocking

## Requirements

- Python 3.12+
- Git (for cloning)
- Virtual environment (recommended)

Optional for storage/alert features:
- Redis server
- PostgreSQL server
- Telegram Bot Token & Chat ID

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/aegisflow-terminal.git
   cd aegisflow-terminal