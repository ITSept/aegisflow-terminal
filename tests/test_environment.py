import asyncio
import sys

def test_python_version():
    assert sys.version_info >= (3, 12), "Python 3.12+ required"

def test_imports():
    import aiohttp
    import websockets
    import dotenv
    # Jika tidak error, import sukses

async def dummy_coro():
    return "ok"

def test_asyncio():
    result = asyncio.run(dummy_coro())
    assert result == "ok"