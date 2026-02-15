# Sonic AI Mod Bot

AI-powered moderation bot for Sonic community Telegram groups.

## Features

- 🤖 **AI-Powered Moderation** - Smart spam and content filtering
- 🛡️ **Anti-Raid Protection** - Auto-detect and block raid attempts
- ⚡ **Auto-Mod** - Configurable strikes, mutes, and kicks
- 👋 **Welcome/Leave Messages** - Customizable greetings
- 📊 **XP & Levels** - Engagement tracking and rewards
- 📝 **Advanced Logging** - Full audit trail
- 🎫 **Ticket Integration** - Link to support system

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env

# Run the bot
python -m bot.main
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `BOT_TOKEN` | Your Telegram bot token from @BotFather |
| `API_ID` | Telegram API ID (my.telegram.org) |
| `API_HASH` | Telegram API Hash |
| `OWNER_ID` | Your Telegram user ID |
| `GROUP_CHAT_ID` | The group chat ID to moderate |
| `LOG_CHANNEL_ID` | Channel for moderation logs |
| `DATABASE_URL` | SQLite or PostgreSQL connection string |
| `NOTION_API_KEY` | Notion API key (for ticket integration) |
| `N8N_WEBHOOK_URL` | n8n webhook for ticket creation |

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Start the bot |
| `/ping` | Bot responsiveness check |
| `/stats` | Group statistics |
| `/ban` | Ban a user (admin) |
| `/mute` | Mute a user (admin) |
| `/kick` | Kick a user (admin) |
| `/warn` | Warn a user (admin) |
| `/settings` | Configure bot settings (admin) |

## Ticket Integration

The bot integrates with [Sonic_Support](https://github.com/MisterMinter/Sonic_Support) for ticket management. When users need support, they can be directed to the ticket system via `/support` command.

## License

MIT
