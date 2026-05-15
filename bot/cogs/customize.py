from __future__ import annotations

  import base64

  import discord
  from discord import app_commands
  from discord.ext import commands

  from utils.logger import get_logger

  logger = get_logger(__name__)


  def _admin_only(interaction: discord.Interaction) -> bool:
      member = interaction.user
      if not isinstance(member, discord.Member):
          return False
      return member.guild_permissions.administrator


  def _to_data_uri(image_bytes: bytes, content_type: str = "image/png") -> str:
      encoded = base64.b64encode(image_bytes).decode("utf-8")
      return f"data:{content_type};base64,{encoded}"


  class CustomizeCog(commands.Cog, name="Customize"):
      """Per-server bot appearance customization commands."""

      def __init__(self, bot: commands.Bot) -> None:
          self.bot = bot

      def _require_guild(self, interaction: discord.Interaction) -> bool:
          return interaction.guild_id is not None

      @app_commands.command(
          name="customize-name",
          description="Set the bot nickname in this server. Requires Administrator.",
      )
      @app_commands.describe(name="The nickname to set. Leave blank to reset to default.")
      async def customize_name(
          self, interaction: discord.Interaction, name: str | None = None
      ) -> None:
          if not _admin_only(interaction):
              await interaction.response.send_message(
                  "You need the Administrator permission to use this command.", ephemeral=True
              )
              return
          if not self._require_guild(interaction):
              await interaction.response.send_message(
                  "This command can only be used inside a server.", ephemeral=True
              )
              return
          try:
              await interaction.guild.me.edit(nick=name)
              msg = f"Nickname set to {name}." if name else "Nickname has been reset."
              await interaction.response.send_message(msg, ephemeral=True)
              logger.info("Guild %s: bot nickname set to '%s'.", interaction.guild_id, name)
          except discord.HTTPException as exc:
              await interaction.response.send_message(f"Failed to update nickname: {exc}", ephemeral=True)

      @app_commands.command(
          name="customize-pfp",
          description="Set the bot profile picture for this server. Requires Administrator.",
      )
      @app_commands.describe(image="Upload an image to use as the profile picture.")
      async def customize_pfp(
          self, interaction: discord.Interaction, image: discord.Attachment
      ) -> None:
          if not _admin_only(interaction):
              await interaction.response.send_message(
                  "You need the Administrator permission to use this command.", ephemeral=True
              )
              return
          if not self._require_guild(interaction):
              await interaction.response.send_message(
                  "This command can only be used inside a server.", ephemeral=True
              )
              return
          await interaction.response.defer(ephemeral=True)
          try:
              image_bytes = await image.read()
              content_type = image.content_type or "image/png"
              data_uri = _to_data_uri(image_bytes, content_type)
              route = discord.http.Route(
                  "PATCH",
                  "/guilds/{guild_id}/members/@me",
                  guild_id=interaction.guild_id,
              )
              await self.bot.http.request(route, json={"avatar": data_uri})
              await interaction.followup.send("Profile picture updated for this server.", ephemeral=True)
              logger.info("Guild %s: bot avatar updated.", interaction.guild_id)
          except Exception as exc:
              logger.exception("Failed to update guild avatar.")
              await interaction.followup.send(f"Failed to update profile picture: {exc}", ephemeral=True)

      @app_commands.command(
          name="customize-banner",
          description="Set the bot profile banner for this server. Requires Administrator.",
      )
      @app_commands.describe(image="Upload an image to use as the banner.")
      async def customize_banner(
          self, interaction: discord.Interaction, image: discord.Attachment
      ) -> None:
          if not _admin_only(interaction):
              await interaction.response.send_message(
                  "You need the Administrator permission to use this command.", ephemeral=True
              )
              return
          if not self._require_guild(interaction):
              await interaction.response.send_message(
                  "This command can only be used inside a server.", ephemeral=True
              )
              return
          await interaction.response.defer(ephemeral=True)
          try:
              image_bytes = await image.read()
              content_type = image.content_type or "image/png"
              data_uri = _to_data_uri(image_bytes, content_type)
              route = discord.http.Route(
                  "PATCH",
                  "/guilds/{guild_id}/members/@me",
                  guild_id=interaction.guild_id,
              )
              await self.bot.http.request(route, json={"banner": data_uri})
              await interaction.followup.send("Banner updated for this server.", ephemeral=True)
              logger.info("Guild %s: bot banner updated.", interaction.guild_id)
          except Exception as exc:
              logger.exception("Failed to update guild banner.")
              await interaction.followup.send(f"Failed to update banner: {exc}", ephemeral=True)

      @app_commands.command(
          name="customize-bio",
          description="Set the bot bio for this server. Requires Administrator.",
      )
      @app_commands.describe(bio="The bio text to display on the bot profile.")
      async def customize_bio(
          self, interaction: discord.Interaction, bio: str
      ) -> None:
          if not _admin_only(interaction):
              await interaction.response.send_message(
                  "You need the Administrator permission to use this command.", ephemeral=True
              )
              return
          if not self._require_guild(interaction):
              await interaction.response.send_message(
                  "This command can only be used inside a server.", ephemeral=True
              )
              return
          await interaction.response.defer(ephemeral=True)
          try:
              route = discord.http.Route(
                  "PATCH",
                  "/guilds/{guild_id}/members/@me",
                  guild_id=interaction.guild_id,
              )
              await self.bot.http.request(route, json={"bio": bio})
              await interaction.followup.send("Bio updated for this server.", ephemeral=True)
              logger.info("Guild %s: bot bio updated.", interaction.guild_id)
          except Exception as exc:
              logger.exception("Failed to update guild bio.")
              await interaction.followup.send(f"Failed to update bio: {exc}", ephemeral=True)

      @app_commands.command(
          name="customize-embeds",
          description="Set the embed color used in this server. Requires Administrator.",
      )
      @app_commands.describe(color="Hex color code, for example FF5733 or #FF5733.")
      async def customize_embeds(
          self, interaction: discord.Interaction, color: str
      ) -> None:
          if not _admin_only(interaction):
              await interaction.response.send_message(
                  "You need the Administrator permission to use this command.", ephemeral=True
              )
              return
          if not self._require_guild(interaction):
              await interaction.response.send_message(
                  "This command can only be used inside a server.", ephemeral=True
              )
              return
          cleaned = color.lstrip("#").strip()
          try:
              color_int = int(cleaned, 16)
              if not (0 <= color_int <= 0xFFFFFF):
                  raise ValueError
          except ValueError:
              await interaction.response.send_message(
                  "Invalid color. Please provide a hex code such as FF5733 or #FF5733.", ephemeral=True
              )
              return
          await self.bot.guild_settings.set_embed_color(interaction.guild_id, color_int)
          embed = discord.Embed(
              description=f"Embed color set to #{cleaned.upper()}.",
              color=color_int,
          )
          await interaction.response.send_message(embed=embed, ephemeral=True)
          logger.info("Guild %s: embed color set to #%s.", interaction.guild_id, cleaned.upper())


  async def setup(bot: commands.Bot) -> None:
      await bot.add_cog(CustomizeCog(bot))
  