"""
Thin async client for the A House Divided public API.
"""

import asyncio
import logging
import os

import aiohttp

log = logging.getLogger("ahd-api")

BASE_URL = "https://ahousedividedgame.com/api/public/v1"


class AhdApi:
    def __init__(self):
        self.api_key = os.environ.get("AHD_API_KEY", "")
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "X-API-Key": self.api_key,
                    "User-Agent": "AHD-AlertBot/2.0",
                }
            )
        return self._session

    async def get(self, path: str, params: dict = None) -> dict | None:
        session = await self._get_session()
        url = f"{BASE_URL}/{path.lstrip('/')}"
        for attempt in range(3):
            try:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
                    if r.status == 429:
                        retry_after = int(r.headers.get("Retry-After", 5))
                        log.warning(f"Rate limited — sleeping {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue
                    if r.status != 200:
                        log.warning(f"HTTP {r.status} from {url}")
                        return None
                    return await r.json()
            except Exception as e:
                log.error(f"Request failed ({url}): {e}")
                if attempt < 2:
                    await asyncio.sleep(2)
        return None

    async def close(self):
        if self._session:
            await self._session.close()
