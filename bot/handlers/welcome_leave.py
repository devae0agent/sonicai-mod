"""Welcome and Leave Message Handler for Sonic AI Mod Bot."""
import re
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class WelcomeConfig:
    """Configuration for welcome messages."""
    enabled: bool = True
    message: str = "👋 Welcome {user}!"
    buttons: List[dict] = None  # [{"text": "Rules", "url": "..."}]
    media: Optional[str] = None  # URL to image/video
    reply_to_message: Optional[int] = None
    delete_after: Optional[int] = None  # seconds


@dataclass
class LeaveConfig:
    """Configuration for leave messages."""
    enabled: bool = True
    message: str = "👋 {user} left us"


class WelcomeLeaveHandler:
    """Handles welcome and leave messages."""

    # Placeholders
    PLACEHOLDERS = {
        "{user}": lambda user: f"@{user.username}" if user.username else f"[{user.first_name}](tg://user?id={user.id})",
        "{first_name}": lambda user: user.first_name or "User",
        "{last_name}": lambda user: user.last_name or "",
        "{user_id}": lambda user: str(user.id),
        "{count}": lambda ctx: str(ctx.get("member_count", 0)),
        "{title}": lambda ctx: ctx.get("chat_title", "this chat"),
    }

    def __init__(self, client=None):
        self.client = client
        self.welcome_configs: Dict[int, WelcomeConfig] = {}  # chat_id -> config
        self.leave_configs: Dict[int, LeaveConfig] = {}  # chat_id -> config
        
        # Auto-welcome for any new chat by default
        default_welcome = WelcomeConfig(
            enabled=True,
            message="👋 Welcome {user} to {title}! 🎉"
        )
        default_leave = LeaveConfig(
            enabled=True,
            message="👋 {user} left the chat"
        )
        
        # Store as class defaults
        self._default_welcome = default_welcome
        self._default_leave = default_leave

    def format_message(self, template: str, user, context: dict = None) -> str:
        """Format a message template with user/chat data."""
        context = context or {}
        result = template
        
        for placeholder, formatter in self.PLACEHOLDERS.items():
            if placeholder in result:
                try:
                    if placeholder == "{count}" or placeholder == "{title}":
                        value = formatter(context)
                    else:
                        value = formatter(user)
                    result = result.replace(placeholder, value)
                except Exception:
                    result = result.replace(placeholder, "[Unknown]")
        
        return result

    async def send_welcome(self, event, user):
        """Send welcome message for a new user."""
        chat = await event.get_chat()
        chat_id = chat.id
        
        # Get config (chat-specific or default)
        config = self.welcome_configs.get(chat_id, self._default_welcome)
        
        if not config.enabled:
            return
        
        # Build context for placeholders
        try:
            participants = await self.client.get_participants(chat)
            member_count = len(participants)
        except:
            member_count = 0
        
        context = {
            "member_count": member_count,
            "chat_title": chat.title or "this chat",
        }
        
        # Format the message
        message = self.format_message(config.message, user, context)
        
        # Send the message
        try:
            sent = await self.client.send_message(
                chat_id,
                message,
                file=config.media,
                buttons=config.buttons,
                reply_to=config.reply_to_message
            )
            
            # Auto-delete if configured
            if config.delete_after:
                import asyncio
                asyncio.create_task(self._delete_after(sent, config.delete_after))
            
            return sent
            
        except Exception as e:
            print(f"Error sending welcome message: {e}")
            return None

    async def send_leave(self, event, user):
        """Send leave message when user leaves."""
        chat = await event.get_chat()
        chat_id = chat.id
        
        # Get config (chat-specific or default)
        config = self.leave_configs.get(chat_id, self._default_leave)
        
        if not config.enabled:
            return
        
        # Format the message
        message = self.format_message(config.message, user, {"chat_title": chat.title})
        
        # Send the message
        try:
            await self.client.send_message(chat_id, message)
        except Exception as e:
            print(f"Error sending leave message: {e}")

    async def _delete_after(self, message, seconds: int):
        """Delete a message after specified seconds."""
        import asyncio
        await asyncio.sleep(seconds)
        try:
            await message.delete()
        except:
            pass

    # Admin configuration methods
    
    def set_welcome(self, chat_id: int, config: WelcomeConfig):
        """Set welcome config for a chat."""
        self.welcome_configs[chat_id] = config

    def set_leave(self, chat_id: int, config: LeaveConfig):
        """Set leave config for a chat."""
        self.leave_configs[chat_id] = config

    def disable_welcome(self, chat_id: int):
        """Disable welcome messages for a chat."""
        if chat_id in self.welcome_configs:
            self.welcome_configs[chat_id].enabled = False
        else:
            self.welcome_configs[chat_id] = WelcomeConfig(enabled=False)

    def disable_leave(self, chat_id: int):
        """Disable leave messages for a chat."""
        if chat_id in self.leave_configs:
            self.leave_configs[chat_id].enabled = False
        else:
            self.leave_configs[chat_id] = LeaveConfig(enabled=False)

    def get_welcome_config(self, chat_id: int) -> WelcomeConfig:
        """Get welcome config for a chat."""
        return self.welcome_configs.get(chat_id, self._default_welcome)

    def get_leave_config(self, chat_id: int) -> LeaveConfig:
        """Get leave config for a chat."""
        return self.leave_configs.get(chat_id, self._default_leave)
