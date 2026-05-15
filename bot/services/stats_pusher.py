from __future__ import annotations

import base64
import json
from typing import Any

import aiohttp

from utils.logger import get_logger

logger = get_logger(__name__)

_GITHUB_API = "https://api.github.com"
_STATS_PATH = "stats.json"


class StatsPusher:
    """Pushes a stats.json file to a GitHub Pages repository via the GitHub API."""

    def __init__(self, pat: str, repo: str) -> None:
        self._pat = pat
        self._repo = repo
        self._headers = {
            "Authorization": f"token {pat}",
            "Accept": "application/vnd.github.v3+json",
        }

    async def push(self, data: dict[str, Any]) -> None:
        url = f"{_GITHUB_API}/repos/{self._repo}/contents/{_STATS_PATH}"
        payload = json.dumps(data, indent=2)
        encoded = base64.b64encode(payload.encode()).decode()
        async with aiohttp.ClientSession() as session:
            sha: str | None = None
            async with session.get(url, headers=self._headers) as r:
                if r.status == 200:
                    existing = await r.json()
                    sha = existing.get("sha")
            body: dict[str, Any] = {
                "message": f"chore: update stats [{data.get('updated_at', 'now')}]",
                "content": encoded,
            }
            if sha:
                body["sha"] = sha
            async with session.put(url, headers=self._headers, json=body) as r:
                if r.status in (200, 201):
                    logger.info("Stats pushed to GitHub Pages successfully.")
                else:
                    text = await r.text()
                    logger.error("Stats push failed: %s %s", r.status, text[:200])