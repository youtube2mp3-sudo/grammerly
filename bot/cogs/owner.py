from __future__ import annotations

import os
import sys

import discord
from discord.ext import commands

from utils.logger import get_logger

logger = get_logger(__name__)

_OWNER_ID = 1169222734069366814


def _parse_words(raw: str) -> list[str]:
    """Split on commas, strip and lowercase each token."""
    return [t.strip().lower() for t in raw.split(",") if t.strip()]


class OwnerCog(commands.Cog, name="Owner"):
    """Owner-only prefix commands (g!whitelist, g!restart, g!db)."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def _is_owner(self, ctx: commands.Context) -> bool:
        return ctx.author.id == _OWNER_ID

    # g!whitelist <word/s>

    @commands.command(name="whitelist")
    async def global_whitelist(self, ctx: commands.Context, *, words: str) -> None:
        if not self._is_owner(ctx):
            return

        tokens = _parse_words(words)
        if not tokens:
            await ctx.reply("No valid words provided.")
            return

        if len(tokens) == 1:
            added = await self.bot.whitelist_service.add_global_word(tokens[0])
            if added:
                msg = f"Added '{tokens[0]}' to the global whitelist."
            else:
                msg = f"'{tokens[0]}' is already in the global whitelist."
            await ctx.reply(msg)
            logger.info("Owner added global word: '%s' (added=%s).", tokens[0], added)
            return

        added_count, skipped_count = await self.bot.whitelist_service.add_global_words_batch(tokens)
        if added_count == 0:
            msg = "All words already exist in the global whitelist."
        elif skipped_count == 0:
            noun = "word" if added_count == 1 else "words"
            msg = f"Added {added_count} {noun} to the global whitelist."
        else:
            noun = "word" if added_count == 1 else "words"
            msg = f"Added {added_count} {noun}. {skipped_count} already existed."
        await ctx.reply(msg)
        logger.info(
            "Owner batch global whitelist: added=%d skipped=%d.", added_count, skipped_count
        )

    # g!restart

    @commands.command(name="restart")
    async def restart(self, ctx: commands.Context) -> None:
        if not self._is_owner(ctx):
            return
        await ctx.reply("Restarting...")
        logger.info("Owner triggered bot restart via g!restart.")
        os.execv(sys.executable, [sys.executable] + sys.argv)

    # g!db

    @commands.command(name="db")
    async def db_status(self, ctx: commands.Context) -> None:
        if not self._is_owner(ctx):
            return

        try:
            pool = self.bot.db.pool
            async with pool.acquire() as conn:
                counts = {}
                for table in ("guild_settings", "global_whitelist", "guild_whitelist", "corrections"):
                    row = await conn.fetchrow(f"SELECT COUNT(*) AS n FROM {table}")
                    counts[table] = row["n"]

                size_row = await conn.fetchrow(
                    "SELECT pg_size_pretty(pg_database_size(current_database())) AS size,"
                    " current_database() AS name"
                )
                db_name = size_row["name"]
                db_size = size_row["size"]

            pool_size  = pool.get_size()
            pool_idle  = pool.get_idle_size()
            pool_min   = pool.get_min_size()
            pool_max   = pool.get_max_size()
            active     = pool_size - pool_idle
        except Exception as exc:
            await ctx.reply(f"Database error: {exc}")
            return

        lines = [
            f"Database : {db_name}",
            f"Size     : {db_size}",
            "",
            "Table row counts:",
            f"  guild_settings   : {counts['guild_settings']}",
            f"  global_whitelist : {counts['global_whitelist']}",
            f"  guild_whitelist  : {counts['guild_whitelist']}",
            f"  corrections      : {counts['corrections']}",
            "",
            f"Connection pool  : min={pool_min}  max={pool_max}",
            f"Active / idle    : {active} / {pool_idle}",
        ]
        await ctx.reply("```\n" + "\n".join(lines) + "\n```")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(OwnerCog(bot))