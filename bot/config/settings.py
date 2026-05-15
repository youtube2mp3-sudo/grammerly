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

      SPELL_DISTANCE: int = 1
      MIN_WORD_LENGTH: int = 3
  