from __future__ import annotations

import asyncio
import datetime
import time

from discord.ext import commands, tasks

from services.stats_pusher import StatsPusher
from services.tracker import CorrectionTracker
from utils.logger import get_logger

logger = get_logger(__name__)


def _get_memory_mb() -> float:
    """Read resident set size from /proc/self/status (Linux)."""
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    kb = int(line.split()[1])
                    return round(kb / 1024, 1)
    except Exception:
        pass
    return 0.0


def _format_uptime(seconds: float) -> str:
    d, rem = divmod(int(seconds), 86400)
    h, rem = divmod(rem, 3600)
    m, s = divmod(rem, 60)
    if d:
        return f"{d}d {h}h {m}m"
    if h:
        return f"{h}h {m}m"
    return f"{m}m {s}s"


class StatsCog(commands.Cog, name="Stats"):
    """Periodic task that pushes live bot statistics to the GitHub Pages site."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._pusher: StatsPusher | None = None
        self._tracker = CorrectionTracker(bot.db)
        self.push_stats_task.start()

    def cog_unload(self) -> None:
        self.push_stats_task.cancel()

    def _get_pusher(self) -> StatsPusher | None:
        pat = getattr(self.bot.settings, "GITHUB_STATS_PAT", "")
        repo = getattr(self.bot.settings, "GITHUB_STATS_REPO", "")
        if not pat or not repo:
            logger.warning("GITHUB_STATS_PAT or GITHUB_STATS_REPO not configured, skipping stats push.")
            return None
        if self._pusher is None:
            self._pusher = StatsPusher(pat, repo)
        return self._pusher

    @tasks.loop(minutes=5)
    async def push_stats_task(self) -> None:
        pusher = self._get_pusher()
        if pusher is None:
            return
        await self._push(pusher)

    @push_stats_task.before_loop
    async def before_push_stats(self) -> None:
        await self.bot.wait_until_ready()
        await asyncio.sleep(5)

    async def _push(self, pusher: StatsPusher) -> None:
        try:
            server_count = len(self.bot.guilds)
            total_corrections = await self._tracker.get_total_corrections()
            latency_ms = round(self.bot.latency * 1000)
            memory_mb = _get_memory_mb()
            uptime_str = "starting"
            if self.bot.start_time is not None:
                elapsed = time.monotonic() - self.bot.start_time
                uptime_str = _format_uptime(elapsed)
            updated_at = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            data = {
                "servers": server_count,
                "corrections": total_corrections,
                "latency_ms": latency_ms,
                "memory_mb": memory_mb,
                "uptime": uptime_str,
                "status": "online",
                "updated_at": updated_at,
            }
            await pusher.push(data)
        except Exception:
            logger.exception("Error during stats push.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(StatsCog(bot))