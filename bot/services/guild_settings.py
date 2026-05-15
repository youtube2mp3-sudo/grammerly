from __future__ import annotations

from services.database import Database
from utils.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_VISIBILITY = "public"
_DEFAULT_TYPE = "plain"


class GuildSettingsService:
    """Async CRUD layer for per-guild bot settings backed by Supabase PostgreSQL."""

    def __init__(self, db: Database) -> None:
        self._db = db

    async def get_response_visibility(self, guild_id: int) -> str:
        """Return 'public' or 'private' for the guild (default: 'public')."""
        async with self._db.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT response_visibility FROM guild_settings WHERE guild_id = $1",
                str(guild_id),
            )
        return row["response_visibility"] if row else _DEFAULT_VISIBILITY

    async def set_response_visibility(self, guild_id: int, mode: str) -> None:
        """Set visibility mode ('public'|'private') for *guild_id*."""
        async with self._db.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO guild_settings (guild_id, response_visibility, response_type)
                VALUES ($1, $2, $3)
                ON CONFLICT (guild_id) DO UPDATE SET
                    response_visibility = EXCLUDED.response_visibility
                """,
                str(guild_id),
                mode,
                _DEFAULT_TYPE,
            )
        logger.info("Guild %s response_visibility set to '%s'.", guild_id, mode)

    async def get_response_type(self, guild_id: int) -> str:
        """Return 'plain' or 'embed' for the guild (default: 'plain')."""
        async with self._db.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT response_type FROM guild_settings WHERE guild_id = $1",
                str(guild_id),
            )
        return row["response_type"] if row else _DEFAULT_TYPE

    async def set_response_type(self, guild_id: int, mode: str) -> None:
        """Set response type ('plain'|'embed') for *guild_id*."""
        async with self._db.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO guild_settings (guild_id, response_visibility, response_type)
                VALUES ($1, $2, $3)
                ON CONFLICT (guild_id) DO UPDATE SET
                    response_type = EXCLUDED.response_type
                """,
                str(guild_id),
                _DEFAULT_VISIBILITY,
                mode,
            )
        logger.info("Guild %s response_type set to '%s'.", guild_id, mode)

    async def is_ephemeral(self, guild_id: int | None) -> bool:
        """Return True when responses should be ephemeral (visibility = private)."""
        if guild_id is None:
            return False
        mode = await self.get_response_visibility(guild_id)
        return mode == "private"
