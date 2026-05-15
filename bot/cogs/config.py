from __future__ import annotations

  import discord
  from discord import app_commands
  from discord.ext import commands

  from utils.logger import get_logger

  logger = get_logger(__name__)

  _PAGE_SIZE = 25


  def _has_configure_permission(interaction: discord.Interaction) -> bool:
      """Administrator OR Manage Server."""
      member = interaction.user
      if not isinstance(member, discord.Member):
          return False
      perms = member.guild_permissions
      return perms.administrator or perms.manage_guild


  class WhitelistPaginatorView(discord.ui.View):
      """Stateful paginator for /whitelist-view."""

      def __init__(self, entries: list[str], title: str, ephemeral: bool) -> None:
          super().__init__(timeout=120)
          self._entries = entries
          self._title = title
          self._ephemeral = ephemeral
          self._page = 0
          self._total_pages = max(1, -(-len(entries) // _PAGE_SIZE))
          self._update_buttons()

      def _update_buttons(self) -> None:
          self.prev_button.disabled = self._page == 0
          self.next_button.disabled = self._page >= self._total_pages - 1

      def _build_content(self) -> str:
          if not self._entries:
              return "No whitelist entries found."
          start = self._page * _PAGE_SIZE
          page_entries = self._entries[start : start + _PAGE_SIZE]
          lines = [f"**{self._title}**"] + list(page_entries)
          if self._total_pages > 1:
              lines.append(f"\nPage {self._page + 1} of {self._total_pages}")
          return "\n".join(lines)

      @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
      async def prev_button(
          self, interaction: discord.Interaction, button: discord.ui.Button
      ) -> None:
          self._page = max(0, self._page - 1)
          self._update_buttons()
          await interaction.response.edit_message(content=self._build_content(), view=self)

      @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
      async def next_button(
          self, interaction: discord.Interaction, button: discord.ui.Button
      ) -> None:
          self._page = min(self._total_pages - 1, self._page + 1)
          self._update_buttons()
          await interaction.response.edit_message(content=self._build_content(), view=self)

      async def on_timeout(self) -> None:
          for item in self.children:
              if isinstance(item, discord.ui.Button):
                  item.disabled = True


  class ConfigCog(commands.Cog, name="Config"):
      """/configure-visibility, /configure-responses, and /whitelist-view."""

      def __init__(self, bot: commands.Bot) -> None:
          self.bot = bot

      @app_commands.command(
          name="whitelist-view",
          description="Display all whitelisted words and phrases.",
      )
      @app_commands.describe(scope="View this server's whitelist or the global whitelist.")
      @app_commands.choices(
          scope=[
              app_commands.Choice(name="Server", value="server"),
              app_commands.Choice(name="Global", value="global"),
          ]
      )
      async def whitelist_view(
          self, interaction: discord.Interaction, scope: app_commands.Choice[str]
      ) -> None:
          guild_id = interaction.guild_id
          ephemeral = await self.bot.guild_settings.is_ephemeral(guild_id)

          if scope.value == "global":
              entries = await self.bot.whitelist_service.get_global_words()
              title = "Global Whitelisted Words"
          else:
              if guild_id is None:
                  await interaction.response.send_message(
                      "This command can only be used inside a server.", ephemeral=True
                  )
                  return
              entries = await self.bot.whitelist_service.get_server_words(guild_id)
              title = "Server Whitelisted Words"

          if not entries:
              await interaction.response.send_message(
                  f"No whitelist entries found for {scope.name}.", ephemeral=ephemeral
              )
              return

          view = WhitelistPaginatorView(entries, title, ephemeral)
          await interaction.response.send_message(
              view._build_content(),
              view=view if len(entries) > _PAGE_SIZE else discord.utils.MISSING,
              ephemeral=ephemeral,
          )
          logger.debug(
              "/whitelist-view (%s) called by %s: %d entries.",
              scope.value,
              interaction.user,
              len(entries),
          )

      @app_commands.command(
          name="configure-visibility",
          description="Set whether bot responses are private (ephemeral) or public.",
      )
      @app_commands.describe(mode="private = only you see responses | public = everyone sees responses")
      @app_commands.choices(
          mode=[
              app_commands.Choice(name="private", value="private"),
              app_commands.Choice(name="public", value="public"),
          ]
      )
      async def configure_visibility(
          self, interaction: discord.Interaction, mode: app_commands.Choice[str]
      ) -> None:
          if not _has_configure_permission(interaction):
              await interaction.response.send_message(
                  "You do not have permission to configure visibility settings.",
                  ephemeral=True,
              )
              return
          guild_id = interaction.guild_id
          await self.bot.guild_settings.set_response_visibility(guild_id, mode.value)
          label = "private (only you)" if mode.value == "private" else "public (everyone)"
          await interaction.response.send_message(
              f"Response visibility set to {label}.", ephemeral=True
          )
          logger.info(
              "%s (%s) set guild %s visibility to '%s'.",
              interaction.user, interaction.user.id, guild_id, mode.value,
          )

      @app_commands.command(
          name="configure-responses",
          description="Set whether bot responses are plain messages or embeds.",
      )
      @app_commands.describe(type="plain = regular messages (default) | embed = rich embed cards")
      @app_commands.choices(
          type=[
              app_commands.Choice(name="plain", value="plain"),
              app_commands.Choice(name="embed", value="embed"),
          ]
      )
      async def configure_responses(
          self, interaction: discord.Interaction, type: app_commands.Choice[str]
      ) -> None:
          if not _has_configure_permission(interaction):
              await interaction.response.send_message(
                  "You do not have permission to configure response settings.",
                  ephemeral=True,
              )
              return
          guild_id = interaction.guild_id
          await self.bot.guild_settings.set_response_type(guild_id, type.value)
          label = "plain messages" if type.value == "plain" else "rich embeds"
          await interaction.response.send_message(
              f"Response type set to {label}.", ephemeral=True
          )
          logger.info(
              "%s (%s) set guild %s response_type to '%s'.",
              interaction.user, interaction.user.id, guild_id, type.value,
          )


  async def setup(bot: commands.Bot) -> None:
      await bot.add_cog(ConfigCog(bot))
  