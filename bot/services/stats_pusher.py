from __future__ import annotations

import base64
import datetime
import json
from typing import Any

import aiohttp

from utils.logger import get_logger

logger = get_logger(__name__)

_GITHUB_API = "https://api.github.com"
_STATS_PATH   = "stats.json"
_SERVERS_PATH = "servers.json"


class StatsPusher:
    """Pushes stats.json and servers.json to a GitHub Pages repository via the GitHub API."""

    def __init__(self, pat: str, repo: str) -> None:
        self._pat = pat
        self._repo = repo
        self._headers = {
            "Authorization": f"token {pat}",
            "Accept": "application/vnd.github.v3+json",
        }

    async def _put_file(
        self,
        session: aiohttp.ClientSession,
        path: str,
        payload_str: str,
        commit_msg: str,
    ) -> None:
        url = f"{_GITHUB_API}/repos/{self._repo}/contents/{path}"
        encoded = base64.b64encode(payload_str.encode()).decode()

        sha: str | None = None
        async with session.get(url, headers=self._headers) as r:
            if r.status == 200:
                existing = await r.json()
                sha = existing.get("sha")

        body: dict[str, Any] = {"message": commit_msg, "content": encoded}
        if sha:
            body["sha"] = sha

        async with session.put(url, headers=self._headers, json=body) as r:
            if r.status in (200, 201):
                logger.info("Pushed %s to GitHub Pages.", path)
            else:
                text = await r.text()
                logger.error("Failed to push %s: %s %s", path, r.status, text[:200])

    async def push(self, data: dict[str, Any]) -> None:
        """Push aggregate stats to stats.json."""
        payload = json.dumps(data, indent=2)
        msg = f"chore: update stats [{data.get('updated_at', 'now')}]"
        async with aiohttp.ClientSession() as session:
            await self._put_file(session, _STATS_PATH, payload, msg)

    async def push_servers(self, guilds: list[dict[str, Any]]) -> None:
        """Push per-guild data to servers.json."""
        updated_at = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        payload = json.dumps({"guilds": guilds, "updated_at": updated_at}, indent=2)
        msg = f"chore: update servers [{updated_at}]"
        async with aiohttp.ClientSession() as session:
            await self._put_file(session, _SERVERS_PATH, payload, msg)
