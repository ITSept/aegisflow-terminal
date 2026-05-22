# utils/logger.py
"""
Centralized logging configuration with rotation and both console + file output.
"""

import logging
import logging.handlers
import sys
from pathlib import Path

# Create logs directory if it doesn't exist
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

def setup_logger(name: str = "aegisflow", level: int = logging.INFO) -> logging.Logger:
    """
    Configure and return a logger with console and rotating file handlers.

    Args:
        name: Logger name (usually __name__).
        level: Logging level (default INFO).

    Returns:
        logging.Logger instance.
    """
    logger = logging.getLogger(name)
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # Formatter for both handlers
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)-8s [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler (stderr is default, but we use stdout for clarity)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler with rotation: 10 MB per file, keep 5 backups
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / "aegisflow.log",
        maxBytes=10 * 1024 * 1024,   # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

# Pre‑configured root logger for quick import
root_logger = setup_logger()