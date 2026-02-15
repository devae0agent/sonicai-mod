"""Configuration management for Sonic AI Mod Bot."""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass
class Config:
    """Bot configuration loaded from environment variables."""

    # Telegram
    bot_token: str
    api_id: int
    api_hash: str
    owner_id: int

    # Chats
    group_chat_id: int
    log_channel_id: Optional[int] = None

    # Database
    database_url: str = "sqlite+aiosqlite:///./sonicmod.db"

    # Integrations
    notion_api_key: Optional[str] = None
    n8n_webhook_url: Optional[str] = None

    # AI
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    # Moderation
    strike_threshold: int = 3
    auto_mute_duration: int = 3600
    spam_filter_enabled: bool = True
    anti_raid_enabled: bool = True

    @classmethod
    def load(cls, env_path: Optional[Path] = None) -> "Config":
        """Load configuration from .env file."""
        if env_path:
            load_dotenv(env_path)
        else:
            load_dotenv()

        required = ["BOT_TOKEN", "API_ID", "API_HASH", "OWNER_ID", "GROUP_CHAT_ID"]
        missing = [k for k in required if not os.getenv(k)]
        
        if missing:
            raise ValueError(f"Missing required env vars: {missing}")

        return cls(
            bot_token=os.getenv("BOT_TOKEN", ""),
            api_id=int(os.getenv("API_ID", 0)),
            api_hash=os.getenv("API_HASH", ""),
            owner_id=int(os.getenv("OWNER_ID", 0)),
            group_chat_id=int(os.getenv("GROUP_CHAT_ID", 0)),
            log_channel_id=int(os.getenv("LOG_CHANNEL_ID")) if os.getenv("LOG_CHANNEL_ID") else None,
            database_url=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./sonicmod.db"),
            notion_api_key=os.getenv("NOTION_API_KEY"),
            n8n_webhook_url=os.getenv("N8N_WEBHOOK_URL"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            strike_threshold=int(os.getenv("STRIKE_THRESHOLD", 3)),
            auto_mute_duration=int(os.getenv("AUTO_MUTE_DURATION", 3600)),
            spam_filter_enabled=os.getenv("SPAM_FILTER_ENABLED", "true").lower() == "true",
            anti_raid_enabled=os.getenv("ANTI_RAID_ENABLED", "true").lower() == "true",
        )
