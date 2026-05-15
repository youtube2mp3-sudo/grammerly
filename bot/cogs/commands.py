from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.tracker import CorrectionTracker
from utils.helpers import format_uptime
from utils.logger import get_logger

logger = get_logger(__name__)

_HELP_TEXT = """\
**Grammerly — Available Commands**

`/latency` — Show bot latency in milliseconds.
`/uptime` — Show how long the bot has been running.
`/corrections <user>` — Show how many times a user has been corrected in this server.
`/leaderboard-server` — View the correction leaderboard for this server.
`/leaderboard-global <type>` — View the global leaderboard (users or servers).
`/whitelist-word <words>` — Add words to this server's ignore list (comma-separated). Requires Manage Messages.
`/whitelist-view <scope>` — View whitelisted words (this server or global).
`/configure-visibility <mode>` — Set responses to private or public. Requires Manage Server.
`/configure-responses <type>` — Set responses to plain or embed format. Requires Manage Server.
`/support` — Get links to the support server and website.
`/invite` — Get a link to invite Grammerly to your server.
`/vote` — Vote for Grammerly on top.gg.
`/help` — Show this message.\
"""


async def _send(
    interaction: discord.Interaction,
    content: str | None = None,
    embed: discord.Embed | None = None,
    ephemeral: bool = False,
) -> None:
    """Send either an embed or plain text message based on what is provided."""
    if embed is not None:
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
    else:
        await interaction.response.send_message(content, ephemeral=ephemeral)


class CommandsCog(commands.Cog, name="Commands"):
    """General slash commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._tracker = CorrectionTracker(bot.db)

    async def _use_embed(self, guild_id: int | None) -> bool:
        if guild_id is None:
            return False
        return await self.bot.guild_settings.get_response_type(guild_id) == "embed"

    # ── /latency ──────────────────────────────────────────────────────────

    @app_commands.command(name="latency", description="Show bot latency in milliseconds.")
    async def latency(self, interaction: discord.Interaction) -> None:
        guild_id = interaction.guild_id
        ephemeral = await self.bot.guild_settings.is_ephemeral(guild_id)
        ms = round(self.bot.latency * 1000)
        if await self._use_embed(guild_id):
            embed = discord.Embed(title="Latency", description=f"{ms}ms", colour=discord.Colour.blurple())
            await _send(interaction, embed=embed, ephemeral=ephemeral)
        else:
            await _send(interaction, content=f"Latency: {ms}ms", ephemeral=ephemeral)

    # ── /uptime ───────────────────────────────────────────────────────────

    @app_commands.command(name="uptime", description="Show how long the bot has been running.")
    async def uptime(self, interaction: discord.Interaction) -> None:
        guild_id = interaction.guild_id
        ephemeral = await self.bot.guild_settings.is_ephemeral(guild_id)
        if self.bot.start_time is None:
            await _send(interaction, content="Bot is still starting up.", ephemeral=ephemeral)
            return
        uptime_str = format_uptime(self.bot.start_time)
        if await self._use_embed(guild_id):
            embed = discord.Embed(title="Uptime", description=uptime_str, colour=discord.Colour.blurple())
            await _send(interaction, embed=embed, ephemeral=ephemeral)
        else:
            await _send(interaction, content=f"Uptime: {uptime_str}", ephemeral=ephemeral)

    # ── /corrections <user> ───────────────────────────────────────────────

    @app_commands.command(
        name="corrections",
        description="Show how many times a user has been spell-corrected in this server.",
    )
    @app_commands.describe(user="The user to look up.")
    async def corrections(
        self, interaction: discord.Interaction, user: discord.Member
    ) -> None:
        guild_id = interaction.guild_id
        ephemeral = await self.bot.guild_settings.is_ephemeral(guild_id)
        count = await self._tracker.get_count(user.id, guild_id) if guild_id else 0

        if count == 0:
            msg = f"{user.display_name} has never been corrected in this server."
        else:
            word = "time" if count == 1 else "times"
            msg = f"{user.display_name} has been corrected **{count}** {word} in this server."

        if await self._use_embed(guild_id):
            embed = discord.Embed(
                title="Corrections",
                description=msg,
                colour=discord.Colour.blurple(),
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            await _send(interaction, embed=embed, ephemeral=ephemeral)
        else:
            await _send(interaction, content=msg, ephemeral=ephemeral)

    # ── /leaderboard-server ───────────────────────────────────────────────

    @app_commands.command(
        name="leaderboard-server",
        description="View the spell-correction leaderboard for this server.",
    )
    async def leaderboard_server(self, interaction: discord.Interaction) -> None:
        guild_id = interaction.guild_id
        if guild_id is None:
            await interaction.response.send_message(
                "This command can only be used inside a server.", ephemeral=True
            )
            return

        ephemeral = await self.bot.guild_settings.is_ephemeral(guild_id)
        rows = await self._tracker.get_server_leaderboard(guild_id, limit=10)

        if not rows:
            msg = "No corrections recorded in this server yet."
            await _send(interaction, content=msg, ephemeral=ephemeral)
            return

        lines = []
        medals = ["🥇", "🥈", "🥉"]
        for i, row in enumerate(rows):
            prefix = medals[i] if i < 3 else f"**{i + 1}.**"
            try:
                user = await self.bot.fetch_user(int(row["user_id"]))
                name = user.display_name
            except Exception:
                name = f"User {row['user_id']}"
            count = row["correction_count"]
            word = "correction" if count == 1 else "corrections"
            lines.append(f"{prefix} {name} — {count} {word}")

        use_embed = await self._use_embed(guild_id)
        if use_embed:
            embed = discord.Embed(
                title=f"Server Leaderboard — {interaction.guild.name}",
                description="\n".join(lines),
                colour=discord.Colour.gold(),
            )
            await _send(interaction, embed=embed, ephemeral=ephemeral)
        else:
            header = f"**Server Leaderboard — {interaction.guild.name}**"
            await _send(interaction, content=header + "\n" + "\n".join(lines), ephemeral=ephemeral)

    # ── /leaderboard-global ───────────────────────────────────────────────

    @app_commands.command(
        name="leaderboard-global",
        description="View the global correction leaderboard across all servers.",
    )
    @app_commands.describe(view="View top users globally, or top servers globally.")
    @app_commands.choices(
        view=[
            app_commands.Choice(name="Users", value="users"),
            app_commands.Choice(name="Servers", value="servers"),
        ]
    )
    async def leaderboard_global(
        self, interaction: discord.Interaction, view: app_commands.Choice[str]
    ) -> None:
        guild_id = interaction.guild_id
        ephemeral = await self.bot.guild_settings.is_ephemeral(guild_id)

        if view.value == "users":
            rows = await self._tracker.get_global_user_leaderboard(limit=10)
            title = "Global Leaderboard — Top Users"
            lines = []
            medals = ["🥇", "🥈", "🥉"]
            for i, row in enumerate(rows):
                prefix = medals[i] if i < 3 else f"**{i + 1}.**"
                try:
                    user = await self.bot.fetch_user(int(row["user_id"]))
                    name = user.display_name
                except Exception:
                    name = f"User {row['user_id']}"
                count = int(row["correction_count"])
                word = "correction" if count == 1 else "corrections"
                lines.append(f"{prefix} {name} — {count} {word}")
        else:
            rows = await self._tracker.get_global_server_leaderboard(limit=10)
            title = "Global Leaderboard — Top Servers"
            lines = []
            medals = ["🥇", "🥈", "🥉"]
            for i, row in enumerate(rows):
                prefix = medals[i] if i < 3 else f"**{i + 1}.**"
                try:
                    guild = await self.bot.fetch_guild(int(row["guild_id"]))
                    name = guild.name
                except Exception:
                    name = f"Server {row['guild_id']}"
                count = int(row["correction_count"])
                word = "correction" if count == 1 else "corrections"
                lines.append(f"{prefix} {name} — {count} {word}")

        if not lines:
            lines = ["No data recorded yet."]

        use_embed = await self._use_embed(guild_id)
        if use_embed:
            embed = discord.Embed(
                title=title,
                description="\n".join(lines),
                colour=discord.Colour.gold(),
            )
            await _send(interaction, embed=embed, ephemeral=ephemeral)
        else:
            await _send(
                interaction,
                content=f"**{title}**\n" + "\n".join(lines),
                ephemeral=ephemeral,
            )

    # ── /support ──────────────────────────────────────────────────────────

    @app_commands.command(
        name="support",
        description="Get a link to the support server and website.",
    )
    async def support(self, interaction: discord.Interaction) -> None:
        guild_id = interaction.guild_id
        ephemeral = await self.bot.guild_settings.is_ephemeral(guild_id)

        support_url = self.bot.settings.SUPPORT_SERVER_URL
        website_url = self.bot.settings.BOT_WEBSITE

        use_embed = await self._use_embed(guild_id)
        if use_embed:
            embed = discord.Embed(
                title="Grammerly Support",
                colour=discord.Colour.blurple(),
            )
            if support_url:
                embed.add_field(name="Support Server", value=f"[Join here]({support_url})", inline=False)
            if website_url:
                embed.add_field(name="Website", value=f"[Visit here]({website_url})", inline=False)
            await _send(interaction, embed=embed, ephemeral=ephemeral)
        else:
            parts = []
            if support_url:
                parts.append(f"**Support Server:** {support_url}")
            if website_url:
                parts.append(f"**Website:** {website_url}")
            if not parts:
                parts.append("Support links are not configured yet.")
            await _send(interaction, content="\n".join(parts), ephemeral=ephemeral)

    # ── /invite ───────────────────────────────────────────────────────────

    @app_commands.command(
        name="invite",
        description="Get a link to invite Grammerly to your server.",
    )
    async def invite(self, interaction: discord.Interaction) -> None:
        guild_id = interaction.guild_id
        ephemeral = await self.bot.guild_settings.is_ephemeral(guild_id)

        bot_id = self.bot.user.id
        permissions = discord.Permissions(
            read_messages=True,
            send_messages=True,
            read_message_history=True,
        )
        invite_url = discord.utils.oauth_url(bot_id, permissions=permissions)

        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="Invite Grammerly",
                url=invite_url,
                style=discord.ButtonStyle.link,
            )
        )

        use_embed = await self._use_embed(guild_id)
        if use_embed:
            embed = discord.Embed(
                title="Invite Grammerly",
                description="Click the button below to add Grammerly to your server!",
                colour=discord.Colour.blurple(),
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=ephemeral)
        else:
            await interaction.response.send_message(
                "Click the button below to add Grammerly to your server!",
                view=view,
                ephemeral=ephemeral,
            )

    # ── /vote ─────────────────────────────────────────────────────────────

    @app_commands.command(
        name="vote",
        description="Vote for Grammerly on top.gg to help keep it online.",
    )
    async def vote(self, interaction: discord.Interaction) -> None:
        guild_id = interaction.guild_id
        ephemeral = await self.bot.guild_settings.is_ephemeral(guild_id)

        topgg_url = self.bot.settings.TOPGG_URL

        use_embed = await self._use_embed(guild_id)
        note = (
            "Voting helps keep Grammerly online and motivates me as a solo developer. "
            "Every vote truly makes a difference — thank you!"
        )

        if use_embed:
            embed = discord.Embed(
                title="Vote for Grammerly",
                description=note,
                colour=discord.Colour.green(),
            )
            if topgg_url:
                embed.add_field(name="top.gg", value=f"[Vote here]({topgg_url})", inline=False)
            await _send(interaction, embed=embed, ephemeral=ephemeral)
        else:
            if topgg_url:
                msg = f"**Vote for Grammerly on top.gg:** {topgg_url}\n\n{note}"
            else:
                msg = f"Voting link is not configured yet.\n\n{note}"
            await _send(interaction, content=msg, ephemeral=ephemeral)

    # ── /help ─────────────────────────────────────────────────────────────

    @app_commands.command(name="help", description="Show all available bot commands.")
    async def help(self, interaction: discord.Interaction) -> None:
        guild_id = interaction.guild_id
        ephemeral = await self.bot.guild_settings.is_ephemeral(guild_id)
        if await self._use_embed(guild_id):
            embed = discord.Embed(
                title="Grammerly — Commands",
                description=_HELP_TEXT,
                colour=discord.Colour.blurple(),
            )
            await _send(interaction, embed=embed, ephemeral=ephemeral)
        else:
            await _send(interaction, content=_HELP_TEXT, ephemeral=ephemeral)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CommandsCog(bot))
