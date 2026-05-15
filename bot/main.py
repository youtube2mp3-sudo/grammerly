import asyncio
import time
import discord
from discord.ext import commands, tasks

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
    "cogs.customize",
    "cogs.owner",
    "cogs.stats",
]


class SpellBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(
            command_prefix=commands.when_mentioned_or("g!"),
            intents=intents,
            help_command=None,
        )

        self.settings = Settings()
        self.db: Database = None
        self.guild_settings: GuildSettingsService = None
        self.whitelist_service: WhitelistService = None
        self.start_time: float = None
        self._presence_tick: int = 0

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

        self.presence_loop.start()

    async def on_ready(self) -> None:
        self.start_time = time.monotonic()
        logger.info("Logged in as %s (ID: %s)", self.user, self.user.id)
        logger.info("Monitoring %d guild(s).", len(self.guilds))
        logger.info("grammerly.xyz")

    @tasks.loop(seconds=30)
    async def presence_loop(self) -> None:
        """Rotate bot presence between server count and total corrections."""
        try:
            server_count = len(self.guilds)

            if self._presence_tick % 2 == 0:
                activity = discord.Activity(
                    type=discord.ActivityType.watching,
                    name=f"{server_count:,} server{'s' if server_count != 1 else ''}",
                )
            else:
                from services.tracker import CorrectionTracker
                tracker = CorrectionTracker(self.db)
                total = await tracker.get_total_corrections()
                activity = discord.Activity(
                    type=discord.ActivityType.watching,
                    name=f"{total:,} correction{'s' if total != 1 else ''} made",
                )

            await self.change_presence(status=discord.Status.online, activity=activity)
            self._presence_tick += 1
        except Exception as exc:
            logger.warning("Presence update failed: %s", exc)

    @presence_loop.before_loop
    async def before_presence_loop(self) -> None:
        await self.wait_until_ready()


async def main() -> None:
    bot = SpellBot()
    async with bot:
        print(BANNER)
        await bot.start(bot.settings.DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
