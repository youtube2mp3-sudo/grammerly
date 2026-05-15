from __future__ import annotations

  import discord
  from discord import app_commands
  from discord.ext import commands

  from services.tracker import CorrectionTracker
  from utils.helpers import format_uptime
  from utils.logger import get_logger

  logger = get_logger(__name__)

  _HELP_PAGES = [
      {
          "title": "Grammerly  /  Info",
          "commands": [
              ("/latency", "Show bot latency in milliseconds."),
              ("/uptime", "Show how long the bot has been running."),
              ("/support", "Get links to the support server and website."),
              ("/invite", "Get a link to invite Grammerly to your server."),
              ("/donate", "Support Grammerly and help keep it running."),
              ("/help", "Show this help menu."),
          ],
      },
      {
          "title": "Grammerly  /  Corrections",
          "commands": [
              ("/corrections <user>", "Show how many times a user has been corrected in this server."),
              ("/leaderboard-server", "View the correction leaderboard for this server."),
              ("/leaderboard-global <type>", "View the global leaderboard for users or servers."),
          ],
      },
      {
          "title": "Grammerly  /  Whitelist",
          "commands": [
              ("/whitelist-word <words>", "Add one or more words to this server's ignore list. Requires Manage Messages."),
              ("/whitelist-view <scope>", "View whitelisted words for this server or globally."),
          ],
      },
      {
          "title": "Grammerly  /  Configuration",
          "commands": [
              ("/configure-visibility <mode>", "Set responses to private or public. Requires Manage Server."),
              ("/configure-responses <type>", "Set responses to plain or embed format. Requires Manage Server."),
              ("/customize-name <name>", "Set the bot nickname for this server. Requires Administrator."),
              ("/customize-pfp <image>", "Set the bot profile picture for this server. Requires Administrator."),
              ("/customize-banner <image>", "Set the bot banner for this server. Requires Administrator."),
              ("/customize-bio <bio>", "Set the bot bio for this server. Requires Administrator."),
              ("/customize-embeds <color>", "Set the embed color for this server. Requires Administrator."),
          ],
      },
  ]


  class HelpPaginatorView(discord.ui.View):
      """Paginated help menu organized by category."""

      def __init__(self, use_embed: bool, color: int) -> None:
          super().__init__(timeout=120)
          self._page = 0
          self._use_embed = use_embed
          self._color = color
          self._total = len(_HELP_PAGES)
          self._update_buttons()

      def _update_buttons(self) -> None:
          self.prev_button.disabled = self._page == 0
          self.next_button.disabled = self._page >= self._total - 1

      def build_embed(self) -> discord.Embed:
          page = _HELP_PAGES[self._page]
          lines = []
          for cmd, desc in page["commands"]:
              lines.append(f"`{cmd}`\n{desc}")
          embed = discord.Embed(
              title=page["title"],
              description="\n\n".join(lines),
              colour=self._color,
          )
          embed.set_footer(text=f"Page {self._page + 1} of {self._total}")
          return embed

      def build_text(self) -> str:
          page = _HELP_PAGES[self._page]
          lines = [f"**{page['title']}**\n"]
          for cmd, desc in page["commands"]:
              lines.append(f"`{cmd}`: {desc}")
          lines.append(f"\nPage {self._page + 1} of {self._total}")
          return "\n".join(lines)

      @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
      async def prev_button(
          self, interaction: discord.Interaction, button: discord.ui.Button
      ) -> None:
          self._page = max(0, self._page - 1)
          self._update_buttons()
          if self._use_embed:
              await interaction.response.edit_message(embed=self.build_embed(), view=self)
          else:
              await interaction.response.edit_message(content=self.build_text(), view=self)

      @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
      async def next_button(
          self, interaction: discord.Interaction, button: discord.ui.Button
      ) -> None:
          self._page = min(self._total - 1, self._page + 1)
          self._update_buttons()
          if self._use_embed:
              await interaction.response.edit_message(embed=self.build_embed(), view=self)
          else:
              await interaction.response.edit_message(content=self.build_text(), view=self)

      async def on_timeout(self) -> None:
          for item in self.children:
              if isinstance(item, discord.ui.Button):
                  item.disabled = True


  async def _send(
      interaction: discord.Interaction,
      content: str | None = None,
      embed: discord.Embed | None = None,
      ephemeral: bool = False,
  ) -> None:
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

      async def _get_color(self, guild_id: int | None) -> int:
          if guild_id is None:
              return 0x5865F2
          return await self.bot.guild_settings.get_embed_color(guild_id)

      @app_commands.command(name="latency", description="Show bot latency in milliseconds.")
      async def latency(self, interaction: discord.Interaction) -> None:
          guild_id = interaction.guild_id
          ephemeral = await self.bot.guild_settings.is_ephemeral(guild_id)
          ms = round(self.bot.latency * 1000)
          if await self._use_embed(guild_id):
              color = await self._get_color(guild_id)
              embed = discord.Embed(title="Latency", description=f"{ms}ms", colour=color)
              await _send(interaction, embed=embed, ephemeral=ephemeral)
          else:
              await _send(interaction, content=f"Latency: {ms}ms", ephemeral=ephemeral)

      @app_commands.command(name="uptime", description="Show how long the bot has been running.")
      async def uptime(self, interaction: discord.Interaction) -> None:
          guild_id = interaction.guild_id
          ephemeral = await self.bot.guild_settings.is_ephemeral(guild_id)
          if self.bot.start_time is None:
              await _send(interaction, content="Bot is still starting up.", ephemeral=ephemeral)
              return
          uptime_str = format_uptime(self.bot.start_time)
          if await self._use_embed(guild_id):
              color = await self._get_color(guild_id)
              embed = discord.Embed(title="Uptime", description=uptime_str, colour=color)
              await _send(interaction, embed=embed, ephemeral=ephemeral)
          else:
              await _send(interaction, content=f"Uptime: {uptime_str}", ephemeral=ephemeral)

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
              msg = f"{user.display_name} has been corrected {count} {word} in this server."
          if await self._use_embed(guild_id):
              color = await self._get_color(guild_id)
              embed = discord.Embed(title="Corrections", description=msg, colour=color)
              embed.set_thumbnail(url=user.display_avatar.url)
              await _send(interaction, embed=embed, ephemeral=ephemeral)
          else:
              await _send(interaction, content=msg, ephemeral=ephemeral)

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
              await _send(interaction, content="No corrections recorded in this server yet.", ephemeral=ephemeral)
              return
          lines = []
          for i, row in enumerate(rows):
              try:
                  user = await self.bot.fetch_user(int(row["user_id"]))
                  name = user.display_name
              except Exception:
                  name = f"User {row['user_id']}"
              count = row["correction_count"]
              word = "correction" if count == 1 else "corrections"
              lines.append(f"{i + 1}. {name}: {count} {word}")
          title = f"Server Leaderboard: {interaction.guild.name}"
          if await self._use_embed(guild_id):
              color = await self._get_color(guild_id)
              embed = discord.Embed(title=title, description="\n".join(lines), colour=color)
              await _send(interaction, embed=embed, ephemeral=ephemeral)
          else:
              await _send(interaction, content=f"**{title}**\n" + "\n".join(lines), ephemeral=ephemeral)

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
          lines = []
          if view.value == "users":
              rows = await self._tracker.get_global_user_leaderboard(limit=10)
              title = "Global Leaderboard: Top Users"
              for i, row in enumerate(rows):
                  try:
                      user = await self.bot.fetch_user(int(row["user_id"]))
                      name = user.display_name
                  except Exception:
                      name = f"User {row['user_id']}"
                  count = int(row["correction_count"])
                  word = "correction" if count == 1 else "corrections"
                  lines.append(f"{i + 1}. {name}: {count} {word}")
          else:
              rows = await self._tracker.get_global_server_leaderboard(limit=10)
              title = "Global Leaderboard: Top Servers"
              for i, row in enumerate(rows):
                  try:
                      guild = await self.bot.fetch_guild(int(row["guild_id"]))
                      name = guild.name
                  except Exception:
                      name = f"Server {row['guild_id']}"
                  count = int(row["correction_count"])
                  word = "correction" if count == 1 else "corrections"
                  lines.append(f"{i + 1}. {name}: {count} {word}")
          if not lines:
              lines = ["No data recorded yet."]
          if await self._use_embed(guild_id):
              color = await self._get_color(guild_id)
              embed = discord.Embed(title=title, description="\n".join(lines), colour=color)
              await _send(interaction, embed=embed, ephemeral=ephemeral)
          else:
              await _send(interaction, content=f"**{title}**\n" + "\n".join(lines), ephemeral=ephemeral)

      @app_commands.command(name="support", description="Get a link to the support server and website.")
      async def support(self, interaction: discord.Interaction) -> None:
          guild_id = interaction.guild_id
          ephemeral = await self.bot.guild_settings.is_ephemeral(guild_id)
          support_url = self.bot.settings.SUPPORT_SERVER_URL
          website_url = self.bot.settings.BOT_WEBSITE
          if await self._use_embed(guild_id):
              color = await self._get_color(guild_id)
              embed = discord.Embed(title="Grammerly Support", colour=color)
              if support_url:
                  embed.add_field(name="Support Server", value=f"[Join here]({support_url})", inline=False)
              if website_url:
                  embed.add_field(name="Website", value=f"[Visit here]({website_url})", inline=False)
              await _send(interaction, embed=embed, ephemeral=ephemeral)
          else:
              parts = []
              if support_url:
                  parts.append(f"Support Server: {support_url}")
              if website_url:
                  parts.append(f"Website: {website_url}")
              if not parts:
                  parts.append("Support links are not configured yet.")
              await _send(interaction, content="\n".join(parts), ephemeral=ephemeral)

      @app_commands.command(name="invite", description="Get a link to invite Grammerly to your server.")
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
          view.add_item(discord.ui.Button(label="Invite Grammerly", url=invite_url, style=discord.ButtonStyle.link))
          if await self._use_embed(guild_id):
              color = await self._get_color(guild_id)
              embed = discord.Embed(
                  title="Invite Grammerly",
                  description="Click the button below to add Grammerly to your server.",
                  colour=color,
              )
              await interaction.response.send_message(embed=embed, view=view, ephemeral=ephemeral)
          else:
              await interaction.response.send_message(
                  "Click the button below to add Grammerly to your server.",
                  view=view,
                  ephemeral=ephemeral,
              )

      @app_commands.command(name="donate", description="Support Grammerly and help keep it running.")
      async def donate(self, interaction: discord.Interaction) -> None:
          guild_id = interaction.guild_id
          ephemeral = await self.bot.guild_settings.is_ephemeral(guild_id)
          donate_url = self.bot.settings.DONATE_URL
          view = discord.ui.View()
          if donate_url:
              view.add_item(discord.ui.Button(label="Donate", url=donate_url, style=discord.ButtonStyle.link))
          msg = (
              "Grammerly is free and always will be. "
              "If you find it useful, consider donating to help cover hosting costs and keep it running."
          )
          if await self._use_embed(guild_id):
              color = await self._get_color(guild_id)
              embed = discord.Embed(title="Support Grammerly", description=msg, colour=color)
              await interaction.response.send_message(
                  embed=embed,
                  view=view if donate_url else discord.utils.MISSING,
                  ephemeral=ephemeral,
              )
          else:
              await interaction.response.send_message(
                  msg,
                  view=view if donate_url else discord.utils.MISSING,
                  ephemeral=ephemeral,
              )

      @app_commands.command(name="help", description="Show all available Grammerly commands.")
      async def help(self, interaction: discord.Interaction) -> None:
          guild_id = interaction.guild_id
          ephemeral = await self.bot.guild_settings.is_ephemeral(guild_id)
          use_embed = await self._use_embed(guild_id)
          color = await self._get_color(guild_id)
          view = HelpPaginatorView(use_embed=use_embed, color=color)
          if use_embed:
              await interaction.response.send_message(embed=view.build_embed(), view=view, ephemeral=ephemeral)
          else:
              await interaction.response.send_message(view.build_text(), view=view, ephemeral=ephemeral)


  async def setup(bot: commands.Bot) -> None:
      await bot.add_cog(CommandsCog(bot))
  