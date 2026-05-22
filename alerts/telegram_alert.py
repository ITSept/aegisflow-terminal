# alerts/telegram_alert.py
"""
Async Telegram alert sender using aiohttp.
Logs every send attempt (success or failure).
"""

import asyncio
import logging
from typing import Optional

import aiohttp

from utils.logger import setup_logger

logger = setup_logger(__name__)


class TelegramAlert:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.session: Optional[aiohttp.ClientSession] = None
        logger.info("TelegramAlert instance created")

    async def start(self):
        """Initialize HTTP session."""
        self.session = aiohttp.ClientSession()
        logger.info("Telegram alert client started")

    async def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """
        Send a message to Telegram chat.
        Returns True if successful, False otherwise.
        """
        if not self.session:
            logger.error("Cannot send message: session not started")
            return False

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode
        }

        try:
            async with self.session.post(url, json=payload, timeout=10) as resp:
                if resp.status == 200:
                    logger.info(f"Telegram alert sent successfully (chat_id={self.chat_id})")
                    return True
                else:
                    error_text = await resp.text()
                    logger.error(f"Telegram API error: status={resp.status}, response={error_text[:200]}")
                    return False
        except asyncio.TimeoutError:
            logger.error("Telegram request timeout")
            return False
        except aiohttp.ClientError as e:
            logger.error(f"Telegram client error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Telegram message: {e}", exc_info=True)
            return False

    async def stop(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()
            logger.info("Telegram alert client stopped")