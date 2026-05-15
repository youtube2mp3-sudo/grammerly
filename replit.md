# Grammerly

A public-ready Discord spell-correction bot that automatically corrects spelling in a designated channel, with per-server configuration, leaderboards, and Supabase-backed storage.

## Run & Operate

- `cd bot && pip install -r requirements.txt && python main.py` — run the bot
- Required env vars: `DISCORD_TOKEN`, `DATABASE_URL` (Supabase PostgreSQL URL)
- Optional env vars: `TARGET_CHANNEL_ID`, `SUPPORT_SERVER_URL`, `BOT_WEBSITE`, `TOPGG_URL`

## Stack

- Python 3.11+
- discord.py 2.x (slash commands via app_commands)
- asyncpg — PostgreSQL async driver connecting to Supabase
- pyspellchecker — spell checking engine

## Where things live

- `bot/main.py` — entry point, bot class, startup hooks
- `bot/config/settings.py` — all env var loading
- `bot/services/database.py` — asyncpg connection pool
- `bot/services/tracker.py` — correction count reads/writes + leaderboards
- `bot/services/guild_settings.py` — per-server visibility and response type
- `bot/services/whitelist_service.py` — global + per-server whitelist (DB-backed with in-memory cache)
- `bot/services/spellcheck.py` — spell-check logic using WhitelistService
- `bot/cogs/commands.py` — general commands: latency, uptime, corrections, leaderboard-server, leaderboard-global, support, invite, vote, help
- `bot/cogs/config.py` — configure-visibility, configure-responses, whitelist-view
- `bot/cogs/whitelist.py` — whitelist-word (per-server)
- `bot/cogs/listener.py` — on_message handler

## Architecture decisions

- Database is Supabase PostgreSQL via asyncpg — no SQLite, no local files for whitelist
- Whitelist is split: global (applies everywhere) vs per-server (managed by server staff)
- WhitelistService uses in-memory caching: global loaded at startup, per-guild loaded lazily on first use and invalidated on write
- Default response visibility is `public`, default response type is `plain` (no embeds unless configured)
- SpellCheckService.find_corrections() is synchronous; the listener pre-loads the guild cache before calling it

## Product

- Monitors a designated channel and auto-corrects spelling mistakes
- Per-server whitelists let server managers add words to ignore
- Global leaderboard (users and servers) and per-server leaderboard
- Configurable: private vs public responses, plain vs embed format (per server)
- /invite, /support, /vote, /help commands for discoverability

## User preferences

- SQL for Supabase must be provided in chat only — not inserted into the repo
- Do not break, remove, or change anything beyond what is explicitly requested

## Gotchas

- Run `pip install -r requirements.txt` inside the `bot/` directory before starting
- `DATABASE_URL` must be the full Supabase PostgreSQL URI (not the REST/anon key)
- Command tree is synced globally on startup — slash command changes may take up to an hour to propagate on Discord

## Supabase SQL Schema

Run this once in the Supabase SQL Editor before starting the bot:

```sql
CREATE TABLE IF NOT EXISTS corrections (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    correction_count INTEGER NOT NULL DEFAULT 0,
    last_corrected TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, guild_id)
);
CREATE INDEX IF NOT EXISTS idx_corrections_guild ON corrections(guild_id);
CREATE INDEX IF NOT EXISTS idx_corrections_user ON corrections(user_id);

CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id TEXT PRIMARY KEY,
    response_visibility TEXT NOT NULL DEFAULT 'public',
    response_type TEXT NOT NULL DEFAULT 'plain'
);

CREATE TABLE IF NOT EXISTS guild_whitelist (
    id BIGSERIAL PRIMARY KEY,
    guild_id TEXT NOT NULL,
    word TEXT NOT NULL,
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(guild_id, word)
);
CREATE INDEX IF NOT EXISTS idx_guild_whitelist_guild ON guild_whitelist(guild_id);

CREATE TABLE IF NOT EXISTS global_whitelist (
    id BIGSERIAL PRIMARY KEY,
    word TEXT NOT NULL UNIQUE,
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```
