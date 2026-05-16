from __future__ import annotations

import asyncpg

from utils.logger import get_logger

logger = get_logger(__name__)


class Database:
    """Async PostgreSQL wrapper backed by asyncpg connection pool."""

    def __init__(self, database_url: str) -> None:
        self._url = database_url
        self._pool: asyncpg.Pool | None = None

    async def init(self) -> None:
        self._pool = await asyncpg.create_pool(self._url, min_size=2, max_size=10)
        logger.info("Database pool created.")
        await self._run_migrations()

    async def _run_migrations(self) -> None:
        """Apply any pending schema changes idempotently."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                ALTER TABLE guild_settings
                ADD COLUMN IF NOT EXISTS monitored_channel_id BIGINT;
                """
            )
            await conn.execute(
                """
                ALTER TABLE guild_settings
                ADD COLUMN IF NOT EXISTS stopped_channel_id BIGINT;
                """
            )
        logger.info("Schema migrations applied (monitored_channel_id, stopped_channel_id).")

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()
            logger.info("Database pool closed.")

    @property
    def pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("Database.init() has not been called.")
        return self._pool
