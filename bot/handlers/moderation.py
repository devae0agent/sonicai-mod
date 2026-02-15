"""Moderation handlers for Sonic AI Mod Bot."""
import asyncio
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional

from telethon import TelegramClient
from telethon.tl.custom import Message
from telethon.tl.types import User


class ViolationType(Enum):
    """Types of violations."""
    SPAM = "spam"
    SCAM = "scam"
    ADVERTISING = "advertising"
    EXPLICIT = "explicit"
    REPETITIVE = "repetitive"
    RAID = "raid"
    INVITE_SPAM = "invite_spam"


@dataclass
class Violation:
    """A single violation record."""
    user_id: int
    violation_type: ViolationType
    timestamp: datetime
    message_preview: str
    severity: int = 1


@dataclass
class Strike:
    """A strike against a user."""
    user_id: int
    violation: Violation
    expires_at: Optional[datetime] = None


@dataclass
class UserRecord:
    """User record for moderation tracking."""
    user_id: int
    username: Optional[str] = None
    first_seen: datetime = field(default_factory=datetime.now)
    warnings: int = 0
    strikes: List[Strike] = field(default_factory=list)
    xp: int = 0
    level: int = 1
    is_banned: bool = False
    is_muted: bool = False
    mute_expires: Optional[datetime] = None
    note_count: int = 0


class ModerationHandler:
    """Handles all moderation logic."""

    # Keywords that trigger violations
    SPAM_KEYWORDS = [
        "buy now", "click here", "free money", "guaranteed income",
        "make money fast", "limited time offer", "act now",
    ]
    
    SCAM_KEYWORDS = [
        "wallet connect", "verify your wallet", "airdrop claim",
        "double your", "send crypto", "withdraw now",
    ]
    
    # Patterns
    LINK_PATTERN = re.compile(r'https?://\S+|t\.me/\+|telegram\.me/\+')
    REPEAT_PATTERN = re.compile(r'(.)\1{5,}')
    INVITE_PATTERN = re.compile(r't\.me/([a-zA-Z0-9_]+)')

    def __init__(self, client: TelegramClient, config):
        self.client = client
        self.config = config
        self.user_records: Dict[int, UserRecord] = {}
        self.violation_log: List[Violation] = []
        
        # Settings
        self.strike_threshold = config.strike_threshold
        self.mute_duration = config.auto_mute_duration
        self.spam_filter_enabled = config.spam_filter_enabled
        self.anti_raid_enabled = config.anti_raid_enabled
        
        # Raid detection
        self.join_timestamps: List[datetime] = []
        self.raid_threshold = 10  # joins per minute = raid
        
        # Word blacklists
        self.word_blacklist: set = set()
        self.word_whitelist: set = set()

    async def check_message(self, message: Message) -> Optional[Violation]:
        """Check a message for violations. Returns Violation if found."""
        if not message.text:
            return None
            
        text = message.text.lower()
        user_id = message.sender_id
        
        # Check spam keywords
        for keyword in self.SPAM_KEYWORDS:
            if keyword in text:
                return Violation(
                    user_id=user_id,
                    violation_type=ViolationType.SPAM,
                    timestamp=datetime.now(),
                    message_preview=message.text[:50],
                    severity=1
                )
        
        # Check scam keywords
        for keyword in self.SCAM_KEYWORDS:
            if keyword in text:
                return Violation(
                    user_id=user_id,
                    violation_type=ViolationType.SCAM,
                    timestamp=datetime.now(),
                    message_preview=message.text[:50],
                    severity=3  # Higher severity for scams
                )
        
        # Check for links (except allowed)
        if self.LINK_PATTERN.search(text):
            # Allow if user has sufficient XP or is whitelisted
            user_record = self.user_records.get(user_id)
            if not user_record or user_record.level < 5:
                return Violation(
                    user_id=user_id,
                    violation_type=ViolationType.ADVERTISING,
                    timestamp=datetime.now(),
                    message_preview=message.text[:50],
                    severity=1
                )
        
        # Check for repetitive messages
        if self.REPEAT_PATTERN.search(text):
            return Violation(
                user_id=user_id,
                violation_type=ViolationType.REPETITIVE,
                timestamp=datetime.now(),
                message_preview=message.text[:50],
                severity=1
            )
        
        # Check blacklisted words
        for word in self.word_blacklist:
            if word in text:
                return Violation(
                    user_id=user_id,
                    violation_type=ViolationType.EXPLICIT,
                    timestamp=datetime.now(),
                    message_preview=message.text[:50],
                    severity=2
                )
        
        return None

    async def handle_violation(self, message: Message, violation: Violation):
        """Handle a detected violation."""
        user_id = violation.user_id
        chat_id = message.chat_id
        
        # Get or create user record
        if user_id not in self.user_records:
            self.user_records[user_id] = UserRecord(user_id=user_id)
        
        record = self.user_records[user_id]
        
        # Create strike
        strike = Strike(
            user_id=user_id,
            violation=violation,
            expires_at=datetime.now() + timedelta(days=7)
        )
        record.strikes.append(strike)
        
        # Log violation
        self.violation_log.append(violation)
        
        # Take action based on severity and strike count
        total_strikes = len(record.strikes)
        
        try:
            if violation.severity >= 3 or total_strikes >= self.strike_threshold:
                # Ban
                await self.client.edit_permissions(chat_id, user_id, view_only=False)
                await message.reply(f"🚫 User {message.sender_id} has been banned for repeated violations.")
                record.is_banned = True
                
            elif total_strikes >= self.strike_threshold // 2:
                # Mute
                mute_until = datetime.now() + timedelta(seconds=self.mute_duration)
                await self.client.edit_permissions(
                    chat_id, user_id, 
                    send_messages=False,
                    until_date=mute_until
                )
                await message.reply(f"🔇 User {message.sender_id} has been muted for {self.mute_duration // 60} minutes.")
                record.is_muted = True
                record.mute_expires = mute_until
                
            else:
                # Warning
                await message.reply(
                    f"⚠️ Warning {total_strikes}/{self.strike_threshold}: "
                    f"{violation.violation_type.value.title()}\n"
                    f"This is an automated warning."
                )
                record.warnings += 1
                
        except Exception as e:
            # Log but don't crash
            print(f"Error handling violation: {e}")

    async def check_raid(self, user: User, chat_id: int) -> bool:
        """Check if this is a raid attempt. Returns True if detected."""
        if not self.anti_raid_enabled:
            return False
        
        now = datetime.now()
        self.join_timestamps.append(now)
        
        # Clean old timestamps (older than 1 minute)
        cutoff = now - timedelta(minutes=1)
        self.join_timestamps = [t for t in self.join_timestamps if t > cutoff]
        
        # Check if join rate exceeds threshold
        if len(self.join_timestamps) >= self.raid_threshold:
            return True
        
        return False

    async def handle_raid_protection(self, chat_id: int):
        """Activate raid protection mode."""
        # Enable slow mode
        await self.client.edit_permissions(
            chat_id,
            send_messages=True,
            send_media=True,
            send_stickers=True,
            invite_users=False,
        )
        
        # Notify admins (would send to log channel in production)

    def add_blacklist_word(self, word: str):
        """Add a word to the blacklist."""
        self.word_blacklist.add(word.lower())

    def add_whitelist_word(self, word: str):
        """Add a word to the whitelist ( exempt from filters)."""
        self.word_whitelist.add(word.lower())

    def remove_blacklist_word(self, word: str):
        """Remove a word from the blacklist."""
        self.word_blacklist.discard(word.lower())

    def get_user_stats(self, user_id: int) -> Optional[UserRecord]:
        """Get moderation stats for a user."""
        return self.user_records.get(user_id)
