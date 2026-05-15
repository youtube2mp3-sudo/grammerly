from __future__ import annotations

import asyncio
import urllib.parse
from typing import Any

import aiohttp
from spellchecker import SpellChecker

from config.settings import Settings
from services.whitelist_service import WhitelistService
from utils.helpers import extract_words
from utils.logger import get_logger

logger = get_logger(__name__)

_GRAMMARBOT_URL = "https://grammarbot.p.rapidapi.com/check"
_GRAMMARBOT_HOST = "grammarbot.p.rapidapi.com"

# How long to wait for the API before giving up and using local fallback (seconds)
_API_TIMEOUT = 6.0


def _parse_api_response(
    data: dict[str, Any],
    content: str,
    whitelist_fn: Any,
    guild_id: int | None,
) -> list[tuple[str, str]]:
    """
    Parse the LanguageTool-compatible response from GrammarBot API.

    Each match has:
      - offset / length  → the original word/phrase in the text
      - replacements[0]  → the top suggested correction

    We only surface matches that have at least one replacement,
    and skip anything the server whitelist covers.
    """
    matches = data.get("matches", [])
    if not matches:
        return []

    seen: set[str] = set()
    results: list[tuple[str, str]] = []

    for match in matches:
        replacements = match.get("replacements", [])
        if not replacements:
            continue

        offset = match.get("offset", 0)
        length = match.get("length", 0)
        original = content[offset: offset + length].strip()
        correction = replacements[0].get("value", "").strip()

        if not original or not correction or original == correction:
            continue

        # Skip if whitelisted
        orig_lower = original.lower()
        if whitelist_fn(guild_id, orig_lower):
            continue

        if orig_lower in seen:
            continue
        seen.add(orig_lower)

        results.append((original, correction))
        logger.debug("API: '%s' → '%s'", original, correction)

    return results


class SpellCheckService:
    """
    Spell/grammar checker with two layers:

    1. **GrammarBot API** (RapidAPI) — richer, catches grammar + spelling.
       Used when RAPIDAPI_KEY is configured.
    2. **Local pyspellchecker fallback** — used when the API key is absent,
       the request fails, or the API times out.

    The public interface is unchanged:
        corrections = await service.find_corrections(content, guild_id)

    WhitelistService caches must be pre-loaded before calling (same as before).
    """

    def __init__(self, settings: Settings, whitelist: WhitelistService) -> None:
        self._api_key: str = getattr(settings, "RAPIDAPI_KEY", "")
        self._min_length: int = settings.MIN_WORD_LENGTH
        self._whitelist = whitelist

        # Local fallback
        self._checker = SpellChecker(distance=settings.SPELL_DISTANCE)

        if self._api_key:
            logger.info("SpellCheckService ready — GrammarBot API enabled (local fallback active).")
        else:
            logger.info(
                "SpellCheckService ready — RAPIDAPI_KEY not set, using local checker only "
                "(distance=%d, min_word_len=%d).",
                settings.SPELL_DISTANCE,
                settings.MIN_WORD_LENGTH,
            )

    # ── Public async interface ────────────────────────────────────────────────

    async def find_corrections(
        self, content: str, guild_id: int | None = None
    ) -> list[tuple[str, str]]:
        """
        Return a list of (original, corrected) tuples for *content*.

        Tries the GrammarBot API first (if configured); falls back to the local
        pyspellchecker on any error or timeout.
        """
        if self._api_key:
            try:
                result = await asyncio.wait_for(
                    self._api_check(content, guild_id),
                    timeout=_API_TIMEOUT,
                )
                return result
            except asyncio.TimeoutError:
                logger.warning("GrammarBot API timed out after %.1fs — using local fallback.", _API_TIMEOUT)
            except Exception as exc:
                logger.warning("GrammarBot API error (%s) — using local fallback.", exc)

        return self._local_check(content, guild_id)

    # ── GrammarBot API layer ──────────────────────────────────────────────────

    async def _api_check(
        self, content: str, guild_id: int | None
    ) -> list[tuple[str, str]]:
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "x-rapidapi-host": _GRAMMARBOT_HOST,
            "x-rapidapi-key": self._api_key,
        }
        body = urllib.parse.urlencode({"text": content, "language": "en-US"})

        async with aiohttp.ClientSession() as session:
            async with session.post(
                _GRAMMARBOT_URL,
                data=body,
                headers=headers,
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"HTTP {resp.status}: {text[:120]}")
                data: dict[str, Any] = await resp.json(content_type=None)

        # If the API returns an error message instead of matches, fall through
        if "message" in data and "matches" not in data:
            raise RuntimeError(f"API message: {data['message']}")

        return _parse_api_response(
            data,
            content,
            self._whitelist.is_whitelisted_sync,
            guild_id,
        )

    # ── Local fallback layer ──────────────────────────────────────────────────

    def _local_check(
        self, content: str, guild_id: int | None
    ) -> list[tuple[str, str]]:
        """
        Synchronous local spell-check using pyspellchecker.
        Mirrors the original find_corrections() logic exactly.
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
                logger.debug("local: '%s' → '%s'", word, correction)

        return results
