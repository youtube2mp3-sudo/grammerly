from __future__ import annotations

from spellchecker import SpellChecker

from config.settings import Settings
from services.whitelist_service import WhitelistService
from utils.helpers import extract_words
from utils.logger import get_logger

logger = get_logger(__name__)


class SpellCheckService:
    """
    Thin, stateless wrapper around pyspellchecker.

    Uses WhitelistService for both global and per-server whitelist checks.
    find_corrections() is synchronous and relies on WhitelistService's in-memory
    caches — call whitelist_service.ensure_guild_cache(guild_id) before invoking.
    """

    def __init__(self, settings: Settings, whitelist: WhitelistService) -> None:
        self._checker = SpellChecker(distance=settings.SPELL_DISTANCE)
        self._min_length: int = settings.MIN_WORD_LENGTH
        self._whitelist = whitelist
        logger.info(
            "SpellCheckService ready (distance=%d, min_word_len=%d).",
            settings.SPELL_DISTANCE,
            settings.MIN_WORD_LENGTH,
        )

    def find_corrections(
        self, content: str, guild_id: int | None = None
    ) -> list[tuple[str, str]]:
        """
        Parse *content* and return a list of (original, corrected) tuples.

        Requires whitelist caches to be pre-loaded (via ensure_guild_cache).
        """
        ignored_phrase_words: set[str] = set()
        for phrase in self._whitelist.contains_ignored_phrase_sync(guild_id, content):
            for w in phrase.split():
                ignored_phrase_words.add(w.lower())

        words = extract_words(content)

        candidates = [
            w
            for w in words
            if len(w) >= self._min_length
            and not self._whitelist.is_whitelisted_sync(guild_id, w)
            and w not in ignored_phrase_words
        ]

        if not candidates:
            return []

        misspelled = self._checker.unknown(candidates)
        if not misspelled:
            return []

        seen: set[str] = set()
        results: list[tuple[str, str]] = []

        for word in candidates:
            if word not in misspelled or word in seen:
                continue
            seen.add(word)
            correction = self._checker.correction(word)
            if correction and correction != word:
                results.append((word, correction))
                logger.debug("'%s' → '%s'", word, correction)

        return results
