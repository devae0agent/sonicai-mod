"""Sonic AI Mod Bot - Main Entry Point."""
import asyncio
import logging
import signal
from pathlib import Path

from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError

from bot.config import Config


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class SonicModBot:
    """Main bot class handling Telegram client and event handlers."""

    def __init__(self, config: Config):
        self.config = config
        self.client: TelegramClient = None
        self.running = False

    async def start(self):
        """Initialize and start the bot."""
        logger.info("Starting Sonic AI Mod Bot...")

        # Initialize Telegram client
        session_path = Path(__file__).parent.parent / "session"
        session_path.mkdir(exist_ok=True)
        
        self.client = TelegramClient(
            str(session_path / "bot"),
            self.config.api_id,
            self.config.api_hash,
        )

        # Register event handlers
        self._register_handlers()

        # Start the client
        await self.client.start(bot_token=self.config.bot_token)
        
        me = await self.client.get_me()
        logger.info(f"Bot started as @{me.username}")

        self.running = True
        
        # Keep running until disconnected
        await self.client.run_until_disconnected()

    def _register_handlers(self):
        """Register all event handlers."""
        # Ping command
        @self.client.on(events.NewMessage(pattern="/ping"))
        async def ping_handler(event):
            await event.reply("🏓 Pong!")

        # Start command
        @self.client.on(events.NewMessage(pattern="/start"))
        async def start_handler(event):
            await event.reply(
                "👋 Sonic AI Mod Bot!\n\n"
                "I'm here to keep the community safe and awesome.\n"
                "Use /help for commands."
            )

        # Help command
        @self.client.on(events.NewMessage(pattern="/help"))
        async def help_handler(event):
            help_text = """
**Sonic AI Mod Bot Commands**

🤖 **General**
• /start - Start the bot
• /ping - Check bot responsiveness
• /help - Show this help message

⚡ **Moderation** (admin)
• /ban @user - Ban a user
• /mute @user - Mute a user  
• /kick @user - Kick a user
• /warn @user - Warn a user

📊 **Stats**
• /stats - Group statistics
• /top - Top members by XP

🎫 **Support**
• /support - Create a support ticket
"""
            await event.reply(help_text, link_preview=False)

        # Welcome new members
        @self.client.on(events.ChatAction)
        async def welcome_handler(event):
            if event.user_joined:
                # TODO: Send welcome message
                logger.info(f"User joined: {event.user_id}")

        # Handle all messages (for spam filtering)
        @self.client.on(events.NewMessage)
        async def message_handler(event):
            if event.is_private:
                return  # Skip private messages
            
            # TODO: Implement spam filtering
            # TODO: Implement XP/level tracking
            pass

    async def stop(self):
        """Gracefully stop the bot."""
        logger.info("Stopping Sonic AI Mod Bot...")
        self.running = False
        if self.client:
            await self.client.disconnect()


async def main():
    """Main entry point."""
    try:
        config = Config.load()
        bot = SonicModBot(config)

        # Handle shutdown signals
        loop = asyncio.get_event_loop()
        
        def signal_handler(sig, frame):
            logger.info(f"Received signal {sig}, shutting down...")
            asyncio.create_task(bot.stop())

        loop.add_signal_handler(signal.SIGINT, lambda: signal_handler(signal.SIGINT, None))
        loop.add_signal_handler(signal.SIGTERM, lambda: signal_handler(signal.SIGTERM, None))

        await bot.start()

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.info("Copy .env.example to .env and fill in your credentials")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
