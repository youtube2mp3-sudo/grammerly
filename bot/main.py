import asyncio
import discord
from discord.ext import commands

from config.settings import Settings
from utils.logger import get_logger
from services.database import Database
from services.guild_settings import GuildSettingsService
from services.whitelist_service import WhitelistService

logger = get_logger(__name__)

BANNER = """
╔══════════════════════════════════════╗
║         Grammerly  v2.0.0            ║
║   Discord Spell Correction Bot       ║
╚══════════════════════════════════════╝
"""

COGS = [
    "cogs.listener",
    "cogs.commands",
    "cogs.whitelist",
    "cogs.config",
]


class SpellBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            help_command=None,
        )

        self.settings = Settings()
        self.db: Database = None
        self.guild_settings: GuildSettingsService = None
        self.whitelist_service: WhitelistService = None
        self.start_time: float = None

    async def setup_hook(self) -> None:
        self.db = Database(self.settings.DATABASE_URL)
        await self.db.init()
        logger.info("Database initialised.")

        self.guild_settings = GuildSettingsService(self.db)
        logger.info("Guild settings service initialised.")

        self.whitelist_service = WhitelistService(self.db)
        await self.whitelist_service.load_global_cache()
        logger.info("Whitelist service initialised.")

        for cog in COGS:
            await self.load_extension(cog)
            logger.info("Loaded cog: %s", cog)

        synced = await self.tree.sync()
        logger.info("Synced %d slash command(s).", len(synced))

    async def on_ready(self) -> None:
        import time
        self.start_time = time.monotonic()
        logger.info("Logged in as %s (ID: %s)", self.user, self.user.id)
        logger.info("Monitoring channel ID: %s", self.settings.TARGET_CHANNEL_ID)
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="your spelling",
            )
        )

    async def close(self) -> None:
        await self.db.close()
        await super().close()

    async def on_error(self, event_method: str, *args, **kwargs) -> None:
        logger.exception("Unhandled error in event '%s'.", event_method)


async def main() -> None:
    print(BANNER)
    bot = SpellBot()
    async with bot:
        await bot.start(bot.settings.DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
