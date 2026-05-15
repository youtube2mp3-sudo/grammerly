from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils.logger import get_logger

logger = get_logger(__name__)

_PERMISSION_ERROR = "You do not have permission to use this command."
_EMPTY_INPUT = "No valid words provided."


def _has_whitelist_permission(interaction: discord.Interaction) -> bool:
    """Return True if the invoking member holds Administrator or Manage Messages."""
    member = interaction.user
    if not isinstance(member, discord.Member):
        return False
    perms = member.guild_permissions
    return perms.administrator or perms.manage_messages


def _parse_input(raw: str) -> list[str]:
    """Split *raw* on commas, strip whitespace, return lowercase non-empty tokens."""
    return [token.strip().lower() for token in raw.split(",") if token.strip()]


class WhitelistCog(commands.Cog, name="Whitelist"):
    """
    /whitelist-word — add words to this server's whitelist (per-server).
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="whitelist-word",
        description="Add one or more words/phrases (comma-separated) to this server's ignore list.",
    )
    @app_commands.describe(
        word_or_phrase=(
            "Word or phrase to whitelist. Separate multiple entries with commas: "
            "gng, bruh, omg, fr"
        )
    )
    async def whitelist_word(
        self, interaction: discord.Interaction, word_or_phrase: str
    ) -> None:
        if not _has_whitelist_permission(interaction):
            await interaction.response.send_message(_PERMISSION_ERROR, ephemeral=True)
            logger.info(
                "Unauthorised whitelist attempt by %s (%s): '%s'.",
                interaction.user,
                interaction.user.id,
                word_or_phrase,
            )
            return

        tokens = _parse_input(word_or_phrase)
        if not tokens:
            await interaction.response.send_message(_EMPTY_INPUT, ephemeral=True)
            return

        guild_id = interaction.guild_id
        if guild_id is None:
            await interaction.response.send_message(
                "This command can only be used inside a server.", ephemeral=True
            )
            return

        ephemeral = await self.bot.guild_settings.is_ephemeral(guild_id)

        if len(tokens) == 1:
            added = await self.bot.whitelist_service.add_server_word(guild_id, tokens[0])
            msg = "Word added to this server's whitelist." if added else "This word is already whitelisted in this server."
            await interaction.response.send_message(msg, ephemeral=ephemeral)
            if added:
                logger.info(
                    "%s (%s) whitelisted '%s' in guild %s.",
                    interaction.user,
                    interaction.user.id,
                    tokens[0],
                    guild_id,
                )
            return

        added_count, skipped_count = await self.bot.whitelist_service.add_server_words_batch(
            guild_id, tokens
        )

        if added_count == 0:
            msg = "All words already exist in this server's whitelist."
        elif skipped_count == 0:
            word = "word" if added_count == 1 else "words"
            msg = f"Added {added_count} new {word} to this server's whitelist."
        else:
            word = "word" if added_count == 1 else "words"
            msg = f"Added {added_count} new {word}. {skipped_count} already existed."

        await interaction.response.send_message(msg, ephemeral=ephemeral)
        logger.info(
            "%s (%s) batch whitelisted in guild %s: added=%d skipped=%d.",
            interaction.user,
            interaction.user.id,
            guild_id,
            added_count,
            skipped_count,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WhitelistCog(bot))
