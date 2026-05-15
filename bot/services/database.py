from __future__ import annotations

import ssl
import socket
import asyncpg
from urllib.parse import urlparse

from utils.logger import get_logger

logger = get_logger(__name__)


class Database:
    """Async PostgreSQL wrapper backed by asyncpg connection pool."""

    def __init__(self, database_url: str) -> None:
        self._url = database_url
        self._pool: asyncpg.Pool | None = None

    @staticmethod
    def _resolve_ipv4(hostname: str, port: int) -> str:
        """Return an IPv4 address for hostname, or the original hostname if resolution fails."""
        try:
            infos = socket.getaddrinfo(hostname, port, socket.AF_INET, socket.SOCK_STREAM)
            if infos:
                return infos[0][4][0]
        except OSError:
            pass
        return hostname

    async def init(self) -> None:
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False

        parsed = urlparse(self._url)
        hostname = parsed.hostname or ""
        port = parsed.port or 5432
        ipv4 = self._resolve_ipv4(hostname, port)
        logger.info("Resolved DB host %s -> %s", hostname, ipv4)

        self._pool = await asyncpg.create_pool(
            self._url.replace(f"@{hostname}", f"@{ipv4}"),
            min_size=2,
            max_size=10,
            ssl=ssl_ctx,
        )
        logger.info("Database pool created.")

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()
            logger.info("Database pool closed.")

    @property
    def pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("Database.init() has not been called.")
        return self._pool
