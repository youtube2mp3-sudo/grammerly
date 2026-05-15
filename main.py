import os
import sys

# Point Python at the bot/ subdirectory so all its imports resolve correctly
bot_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot")
os.chdir(bot_dir)
sys.path.insert(0, bot_dir)

import asyncio
from main import main as bot_main

if __name__ == "__main__":
    asyncio.run(bot_main())
