"""Sonic AI Mod Bot - Main Entry Point."""
import asyncio
import logging
import os
import signal
from pathlib import Path

from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError

from bot.config import Config
from bot.handlers.moderation import ModerationHandler
from bot.handlers.xp_system import XPHandler
from bot.handlers.audit_logger import AuditLogger, LogType
from bot.handlers.welcome_leave import WelcomeLeaveHandler
from bot.handlers.tickets import TicketHandler, TicketConfig


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
        
        # Initialize handlers
        self.moderation = ModerationHandler(None, config)
        self.xp = XPHandler()
        self.audit = AuditLogger(None, config.log_channel_id)
        self.welcome_leave = WelcomeLeaveHandler()
        self.tickets = TicketHandler(
            None, 
            TicketConfig(
                n8n_webhook_url=config.n8n_webhook_url,
                enabled=bool(config.n8n_webhook_url)
            )
        )

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
        
        # Update handler references
        self.moderation.client = self.client
        self.audit.client = self.client
        self.welcome_leave.client = self.client
        self.tickets.client = self.client

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
        
        # ==================== COMMANDS ====================
        
        @self.client.on(events.NewMessage(pattern="/ping"))
        async def ping_handler(event):
            await event.reply("🏓 Pong!")
            self.audit.log_command(event.sender_id, event.chat_id, "/ping")

        @self.client.on(events.NewMessage(pattern="/start"))
        async def start_handler(event):
            help_text = """
👋 **Sonic AI Mod Bot**

I'm here to keep the community safe and awesome!

**Commands:**
• /ping - Check if I'm alive
• /stats - Group statistics  
• /top - Top members by XP
• /profile - Your profile & XP
• /support - Create a ticket
• /help - Show all commands
"""
            await event.reply(help_text, link_preview=False)

        @self.client.on(events.NewMessage(pattern="/help"))
        async def help_handler(event):
            help_text = """
⚡ **Commands**

**General:**
• /start - Start the bot
• /ping - Ping-pong
• /help - This help message
• /stats - Group statistics
• /top - Leaderboard

**Profile:**
• /profile - Your XP & level
• /level - Current level info

**Support:**
• /support - Create ticket
• /mytickets - Your tickets

**Moderation (admin):**
• /ban @user - Ban user
• /mute @user - Mute user
• /kick @user - Kick user
• /warn @user - Warn user
• /settings - Bot settings
"""
            await event.reply(help_text, link_preview=False)
            self.audit.log_command(event.sender_id, event.chat_id, "/help")

        @self.client.on(events.NewMessage(pattern="/stats"))
        async def stats_handler(event):
            # Get group stats
            try:
                participants = await self.client.get_participants(event.chat_id)
                total_members = len(participants)
                
                # Count messages today (simplified)
                stats_text = f"""
📊 **Group Stats**

👥 Members: {total_members}
🏆 Active XP users: {len(self.xp.user_totals)}
📝 Total violations logged: {len(self.audit.logs)}
🎫 Open tickets: {len(self.tickets.open_tickets)}
"""
                await event.reply(stats_text)
            except Exception as e:
                await event.reply(f"Error getting stats: {e}")
            
            self.audit.log_command(event.sender_id, event.chat_id, "/stats")

        @self.client.on(events.NewMessage(pattern="/top"))
        async def top_handler(event):
            leaderboard = self.xp.get_leaderboard(10)
            
            if not leaderboard:
                await event.reply("No XP data yet!")
                return
            
            text = "🏆 **Top Members**\n\n"
            for entry in leaderboard:
                text += f"{entry['rank']}. Level {entry['level']} {entry['title']} - {entry['xp']} XP\n"
            
            await event.reply(text, link_preview=False)
            self.audit.log_command(event.sender_id, event.chat_id, "/top")

        @self.client.on(events.NewMessage(pattern="/profile"))
        async def profile_handler(event):
            user_id = event.sender_id
            stats = self.xp.get_user_stats(user_id)
            
            text = f"""
👤 **Your Profile**

XP: {stats['total_xp']}
Level: {stats['level']} - {stats['title']}
Progress: {stats['progress']:.1f}% to next level
({stats['xp_to_next']} XP needed)

Messages: {stats['message_count']}
Reactions: {stats['reaction_count']}
"""
            await event.reply(text.strip())
            self.audit.log_command(event.sender_id, event.chat_id, "/profile")

        @self.client.on(events.NewMessage(pattern="/support|/ticket"))
        async def support_handler(event):
            # Extract subject from command
            text = event.text or ""
            parts = text.split(None, 1)
            subject = parts[1] if len(parts) > 1 else "General Support"
            
            # Create ticket
            ticket = await self.tickets.create_ticket(
                user_id=event.sender_id,
                chat_id=event.chat_id,
                subject=subject,
                description="Created via /support command"
            )
            
            if ticket:
                await event.reply(
                    f"🎫 Ticket created!\n\n"
                    f"ID: `{ticket.id}`\n"
                    f"Subject: {ticket.subject}\n\n"
                    f"Our team will respond soon."
                )
                self.audit.log(
                    LogType.TICKET,
                    event.sender_id,
                    event.chat_id,
                    {"ticket_id": ticket.id, "subject": subject}
                )
            else:
                await event.reply(
                    "❌ Could not create ticket.\n"
                    "You may have too many open tickets or be on cooldown."
                )

        @self.client.on(events.NewMessage(pattern="/mytickets"))
        async def mytickets_handler(event):
            tickets = self.tickets.get_user_tickets(event.sender_id)
            
            if not tickets:
                await event.reply("No tickets found.")
                return
            
            text = "🎫 **Your Tickets**\n\n"
            for t in tickets[-5:]:
                text += f"• {t.id}: {t.subject} [{t.status}]\n"
            
            await event.reply(text)

        # ==================== EVENT HANDLERS ====================
        
        @self.client.on(events.ChatAction)
        async def chat_action_handler(event):
            """Handle joins and leaves."""
            
            if event.user_joined:
                user = await event.get_user()
                
                # Check for raid
                is_raid = await self.moderation.check_raid(user, event.chat_id)
                if is_raid:
                    await self.moderation.handle_raid_protection(event.chat_id)
                    await event.reply("🛡️ Raid detected! Protection mode activated.")
                
                # Send welcome
                await self.welcome_leave.send_welcome(event, user)
                
                # Log join
                self.audit.log_join(user.id, event.chat_id, user.username or "")
                
                # Award XP for joining
                self.xp.add_xp(user.id, 10, "join")

            elif event.user_left:
                user = await event.get_user()
                
                # Send leave message
                await self.welcome_leave.send_leave(event, user)
                
                # Log leave
                self.audit.log_leave(user.id, event.chat_id, user.username or "")

        @self.client.on(events.NewMessage)
        async def message_handler(event):
            """Handle all messages - XP and moderation."""
            if event.is_private:
                return  # Skip private messages
            
            user_id = event.sender_id
            chat_id = event.chat_id
            
            # Skip if user is muted/banned
            user_record = self.moderation.user_records.get(user_id)
            if user_record and (user_record.is_banned or user_record.is_muted):
                return
            
            # Check for violations
            if self.moderation.spam_filter_enabled:
                violation = await self.moderation.check_message(event)
                if violation:
                    await self.moderation.handle_violation(event, violation)
                    self.audit.log_violation(
                        user_id, chat_id,
                        violation.violation_type.value,
                        violation.severity
                    )
                    return  # Don't award XP for spam
            
            # Award XP for message
            level_up = await self.xp.reward_message(
                user_id,
                event.text[:50] if event.text else ""
            )
            
            # Log level up
            if level_up:
                self.audit.log_level_up(user_id, chat_id, level_up["old_level"], level_up["new_level"])
                try:
                    await event.reply(
                        f"🎉 Level Up!\n\n"
                        f"You're now level {level_up['new_level']} - {level_up['title']}!"
                    )
                except:
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
        # Load environment
        load_dotenv()
        
        # Load config
        config = Config.load()
        
        # Create and start bot
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
