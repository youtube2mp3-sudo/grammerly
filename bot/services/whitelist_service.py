from __future__ import annotations

import asyncio

from services.database import Database
from utils.logger import get_logger

logger = get_logger(__name__)


class WhitelistService:
    """
    Manages both the global whitelist and per-server (guild) whitelists.

    Global entries apply across every server.
    Guild entries only apply within their server.

    Both are cached in memory for fast synchronous lookups during spell-checking.
    The guild cache is lazily populated on first access per guild and invalidated
    on write.
    """

    def __init__(self, db: Database) -> None:
        self._db = db
        self._global_cache: set[str] = set()
        self._guild_cache: dict[str, set[str]] = {}
        self._lock = asyncio.Lock()

    async def load_global_cache(self) -> None:
        """Load all global whitelist words into memory. Called on startup."""
        async with self._db.pool.acquire() as conn:
            rows = await conn.fetch("SELECT word FROM global_whitelist")
        self._global_cache = {row["word"] for row in rows}
        logger.info("Global whitelist cache loaded: %d entries.", len(self._global_cache))

    async def ensure_guild_cache(self, guild_id: int) -> None:
        """Load a guild's whitelist into cache if not already loaded."""
        guild_key = str(guild_id)
        if guild_key not in self._guild_cache:
            async with self._db.pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT word FROM guild_whitelist WHERE guild_id = $1", guild_key
                )
            self._guild_cache[guild_key] = {row["word"] for row in rows}
            logger.debug(
                "Guild %s whitelist cache loaded: %d entries.",
                guild_id,
                len(self._guild_cache[guild_key]),
            )

    def is_whitelisted_sync(self, guild_id: int | None, word: str) -> bool:
        """
        Synchronous whitelist check using cached data.
        Call ensure_guild_cache() before using this in the listener.
        """
        w = word.lower()
        if w in self._global_cache:
            return True
        if guild_id is not None:
            return w in self._guild_cache.get(str(guild_id), set())
        return False

    def contains_ignored_phrase_sync(self, guild_id: int | None, content: str) -> set[str]:
        """
        Return whitelisted phrases (multi-word entries) found in *content*.
        Uses cached data -- call ensure_guild_cache() first.
        """
        normalised = content.lower()
        found: set[str] = set()
        for entry in self._global_cache:
            if " " in entry and entry in normalised:
                found.add(entry)
        if guild_id is not None:
            for entry in self._guild_cache.get(str(guild_id), set()):
                if " " in entry and entry in normalised:
                    found.add(entry)
        return found

    async def get_global_words(self) -> list[str]:
        """Return all global whitelist words sorted."""
        return sorted(self._global_cache)

    async def get_server_words(self, guild_id: int) -> list[str]:
        """Return all words for a guild sorted."""
        await self.ensure_guild_cache(guild_id)
        return sorted(self._guild_cache.get(str(guild_id), set()))

    async def add_global_word(self, word: str) -> bool:
        """Add *word* to the global whitelist. Returns True if added, False if duplicate."""
        normalised = word.strip().lower()
        if not normalised:
            return False
        if normalised in self._global_cache:
            return False
        async with self._lock:
            if normalised in self._global_cache:
                return False
            async with self._db.pool.acquire() as conn:
                try:
                    await conn.execute(
                        "INSERT INTO global_whitelist (word) VALUES ($1) ON CONFLICT DO NOTHING",
                        normalised,
                    )
                except Exception:
                    return False
            self._global_cache.add(normalised)
        logger.info("Global whitelist: added '%s'.", normalised)
        return True

    async def add_global_words_batch(self, words: list[str]) -> tuple[int, int]:
        """Batch-add words to the global whitelist. Returns (added, skipped)."""
        seen: set[str] = set()
        to_add: list[str] = []
        skipped = 0
        for raw in words:
            normalised = raw.strip().lower()
            if not normalised or normalised in seen:
                continue
            seen.add(normalised)
            if normalised in self._global_cache:
                skipped += 1
            else:
                to_add.append(normalised)
        if not to_add:
            return 0, skipped
        async with self._lock:
            truly_new = [w for w in to_add if w not in self._global_cache]
            skipped += len(to_add) - len(truly_new)
            if truly_new:
                async with self._db.pool.acquire() as conn:
                    await conn.executemany(
                        "INSERT INTO global_whitelist (word) VALUES ($1) ON CONFLICT DO NOTHING",
                        [(w,) for w in truly_new],
                    )
                self._global_cache.update(truly_new)
        logger.info("Global whitelist batch: added %d, skipped %d.", len(truly_new), skipped)
        return len(truly_new), skipped

    async def add_server_word(self, guild_id: int, word: str) -> bool:
        """Add *word* to the guild whitelist. Returns True if added, False if duplicate."""
        normalised = word.strip().lower()
        if not normalised:
            return False
        guild_key = str(guild_id)
        await self.ensure_guild_cache(guild_id)
        if normalised in self._guild_cache.get(guild_key, set()):
            return False
        async with self._lock:
            await self.ensure_guild_cache(guild_id)
            if normalised in self._guild_cache.get(guild_key, set()):
                return False
            async with self._db.pool.acquire() as conn:
                try:
                    await conn.execute(
                        "INSERT INTO guild_whitelist (guild_id, word) VALUES ($1, $2)",
                        guild_key,
                        normalised,
                    )
                except Exception:
                    return False
            self._guild_cache.setdefault(guild_key, set()).add(normalised)
        logger.info("Guild %s whitelisted word: '%s'.", guild_id, normalised)
        return True

    async def add_server_words_batch(
        self, guild_id: int, words: list[str]
    ) -> tuple[int, int]:
        """Batch-add words to the guild whitelist. Returns (added_count, skipped_count)."""
        guild_key = str(guild_id)
        await self.ensure_guild_cache(guild_id)
        existing = self._guild_cache.get(guild_key, set())
        seen: set[str] = set()
        to_add: list[str] = []
        skipped = 0
        for raw in words:
            normalised = raw.strip().lower()
            if not normalised or normalised in seen:
                continue
            seen.add(normalised)
            if normalised in existing:
                skipped += 1
            else:
                to_add.append(normalised)
        if not to_add:
            return 0, skipped
        async with self._lock:
            existing = self._guild_cache.get(guild_key, set())
            truly_new = [w for w in to_add if w not in existing]
            skipped += len(to_add) - len(truly_new)
            if truly_new:
                async with self._db.pool.acquire() as conn:
                    await conn.executemany(
                        "INSERT INTO guild_whitelist (guild_id, word) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                        [(guild_key, w) for w in truly_new],
                    )
                self._guild_cache.setdefault(guild_key, set()).update(truly_new)
        logger.info("Guild %s batch whitelist: added %d, skipped %d.", guild_id, len(truly_new), skipped)
        return len(truly_new), skipped