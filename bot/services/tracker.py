from __future__ import annotations

from services.database import Database
from utils.logger import get_logger

logger = get_logger(__name__)


class CorrectionTracker:
    """Records and queries correction counts, backed by Supabase PostgreSQL."""

    def __init__(self, db: Database) -> None:
        self._db = db

    async def record(self, user_id: int, guild_id: int, count: int = 1) -> None:
        """Persist *count* new corrections for *user_id* in *guild_id*."""
        async with self._db.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO corrections (user_id, guild_id, correction_count, last_corrected)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (user_id, guild_id) DO UPDATE SET
                    correction_count = corrections.correction_count + EXCLUDED.correction_count,
                    last_corrected   = NOW()
                """,
                str(user_id),
                str(guild_id),
                count,
            )
        logger.debug("Recorded %d correction(s) for user %s in guild %s.", count, user_id, guild_id)

    async def get_count(self, user_id: int, guild_id: int) -> int:
        """Return correction count for *user_id* in *guild_id*. Returns 0 if not found."""
        async with self._db.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT correction_count FROM corrections WHERE user_id = $1 AND guild_id = $2",
                str(user_id),
                str(guild_id),
            )
        return row["correction_count"] if row else 0

    async def get_server_leaderboard(self, guild_id: int, limit: int = 10) -> list[dict]:
        """Return top *limit* users in *guild_id* ordered by correction count."""
        async with self._db.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT user_id, correction_count
                FROM corrections
                WHERE guild_id = $1
                ORDER BY correction_count DESC
                LIMIT $2
                """,
                str(guild_id),
                limit,
            )
        return [dict(r) for r in rows]

    async def get_global_user_leaderboard(self, limit: int = 10) -> list[dict]:
        """Return top *limit* users globally ordered by total correction count."""
        async with self._db.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT user_id, SUM(correction_count) AS correction_count
                FROM corrections
                GROUP BY user_id
                ORDER BY correction_count DESC
                LIMIT $1
                """,
                limit,
            )
        return [dict(r) for r in rows]

    async def get_global_server_leaderboard(self, limit: int = 10) -> list[dict]:
        """Return top *limit* servers globally ordered by total correction count."""
        async with self._db.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT guild_id, SUM(correction_count) AS correction_count
                FROM corrections
                GROUP BY guild_id
                ORDER BY correction_count DESC
                LIMIT $1
                """,
                limit,
            )
        return [dict(r) for r in rows]
