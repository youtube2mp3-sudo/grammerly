from __future__ import annotations

import discord
from discord.ext import commands

from services.spellcheck import SpellCheckService
from services.tracker import CorrectionTracker
from utils.logger import get_logger

logger = get_logger(__name__)


class ListenerCog(commands.Cog, name="Listener"):
    """Monitors the target channel and replies with spell corrections."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._spellcheck = SpellCheckService(bot.settings, bot.whitelist_service)
        self._tracker = CorrectionTracker(bot.db)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        if message.channel.id != self.bot.settings.TARGET_CHANNEL_ID:
            return

        if message.type not in (
            discord.MessageType.default,
            discord.MessageType.reply,
        ):
            return

        content = message.content.strip()
        if not content:
            return

        guild_id = message.guild.id if message.guild else None

        # Pre-load guild whitelist cache for synchronous spell-check lookup
        if guild_id is not None:
            await self.bot.whitelist_service.ensure_guild_cache(guild_id)

        corrections = self._spellcheck.find_corrections(content, guild_id)
        if not corrections:
            return

        lines = [f"*{corrected}" for _, corrected in corrections]
        reply_text = "\n".join(lines)

        try:
            await message.reply(reply_text, mention_author=False)
        except discord.HTTPException as exc:
            logger.warning("Failed to send correction reply: %s", exc)
            return

        if guild_id is not None:
            await self._tracker.record(message.author.id, guild_id, len(corrections))

        logger.info(
            "Corrected %d word(s) for user %s (%s) in guild %s.",
            len(corrections),
            message.author,
            message.author.id,
            guild_id,
        )

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ListenerCog(bot))
