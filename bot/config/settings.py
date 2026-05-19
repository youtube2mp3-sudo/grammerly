import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings:
    """Central configuration loaded from environment variables."""

    DISCORD_TOKEN: str = os.environ["BOT_TOKEN"]
    TARGET_CHANNEL_ID: int = int(os.environ.get("TARGET_CHANNEL_ID", "0"))

    DATABASE_URL: str = os.environ["DATABASE_URL"]

    SUPPORT_SERVER_URL: str = os.environ.get("SUPPORT_SERVER_URL", "")
    BOT_WEBSITE: str = os.environ.get("BOT_WEBSITE", "")
    TOPGG_URL: str = os.environ.get("TOPGG_URL", "")
    DONATE_URL: str = os.environ.get("DONATE_URL", "")

    GITHUB_STATS_PAT: str = os.environ.get("GITHUB_STATS_PAT", "")
    GITHUB_STATS_REPO: str = os.environ.get("GITHUB_STATS_REPO", "")

    # RapidAPI key for the GrammarBot grammar+spelling API.
    # When set, the bot uses the API for richer corrections and falls back
    # to the local pyspellchecker if the API is unavailable.
    # Leave blank to use the local checker only.
    RAPIDAPI_KEY: str = os.environ.get("RAPIDAPI_KEY", "")
    LANGUAGETOOL_URL: str = os.environ.get("LANGUAGETOOL_URL", "")

    SPELL_DISTANCE: int = 1
    MIN_WORD_LENGTH: int = 3
