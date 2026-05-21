"""
Async Telegram alert sender using aiohttp.
"""

import asyncio
import logging
from typing import Optional
import aiohttp

logger = logging.getLogger(__name__)

class TelegramAlert:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.session: Optional[aiohttp.ClientSession] = None

    async def start(self):
        self.session = aiohttp.ClientSession()
        logger.info("Telegram alert client initialized")

    async def send_message(self, text: str) -> bool:
        """Send message to Telegram. Returns True if successful."""
        if not self.session:
            return False
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        try:
            async with self.session.post(url, json=payload, timeout=5) as resp:
                if resp.status == 200:
                    logger.info(f"Alert sent: {text[:50]}...")
                    return True
                else:
                    logger.error(f"Telegram send failed: {resp.status}")
                    return False
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            return False

    async def stop(self):
        if self.session:
            await self.session.close()
            logger.info("Telegram client closed")