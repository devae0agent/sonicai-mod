"""Logging and Audit Trail for Sonic AI Mod Bot."""
import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class LogType(Enum):
    """Types of log events."""
    MESSAGE = "message"
    JOIN = "join"
    LEAVE = "leave"
    BAN = "ban"
    MUTE = "mute"
    KICK = "kick"
    WARN = "warn"
    VIOLATION = "violation"
    TICKET = "ticket"
    COMMAND = "command"
    LEVEL_UP = "level_up"
    SPAM = "spam"


@dataclass
class LogEntry:
    """A single log entry."""
    id: str
    timestamp: datetime
    log_type: LogType
    user_id: int
    chat_id: int
    details: dict = field(default_factory=dict)
    message_preview: str = ""
    extra: str = ""


class AuditLogger:
    """Comprehensive audit logging for the bot."""

    def __init__(self, client=None, log_channel_id: Optional[int] = None):
        self.client = client
        self.log_channel_id = log_channel_id
        self.logs: List[LogEntry] = []
        self.log_counter = 0
        
        # In-memory indices for fast lookups
        self.user_logs: Dict[int, List[str]] = {}  # user_id -> log_ids
        self.chat_logs: Dict[int, List[str]] = {}  # chat_id -> log_ids

    def _generate_id(self) -> str:
        """Generate unique log entry ID."""
        self.log_counter += 1
        return f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{self.log_counter}"

    def log(
        self,
        log_type: LogType,
        user_id: int,
        chat_id: int,
        details: dict = None,
        message_preview: str = "",
        extra: str = ""
    ) -> LogEntry:
        """Create a log entry."""
        entry = LogEntry(
            id=self._generate_id(),
            timestamp=datetime.now(),
            log_type=log_type,
            user_id=user_id,
            chat_id=chat_id,
            details=details or {},
            message_preview=message_preview[:100] if message_preview else "",
            extra=extra
        )
        
        self.logs.append(entry)
        
        # Update indices
        if user_id not in self.user_logs:
            self.user_logs[user_id] = []
        self.user_logs[user_id].append(entry.id)
        
        if chat_id not in self.chat_logs:
            self.chat_logs[chat_id] = []
        self.chat_logs[chat_id].append(entry.id)
        
        # Send to log channel if configured
        if self.log_channel_id and self.client:
            asyncio.create_task(self._send_to_channel(entry))
        
        return entry

    async def _send_to_channel(self, entry: LogEntry):
        """Send log entry to the log channel."""
        if not self.client:
            return
            
        emoji = {
            LogType.MESSAGE: "💬",
            LogType.JOIN: "👋",
            LogType.LEAVE: "👋",
            LogType.BAN: "🚫",
            LogType.MUTE: "🔇",
            LogType.KICK: "🦶",
            LogType.WARN: "⚠️",
            LogType.VIOLATION: "⛔",
            LogType.TICKET: "🎫",
            LogType.COMMAND: "🛠️",
            LogType.LEVEL_UP: "⭐",
            LogType.SPAM: "🛡️",
        }.get(entry.log_type, "📝")

        # Format the message
        details_text = ""
        if entry.details:
            details_text = "\n".join(f"  {k}: {v}" for k, v in entry.details.items())
        
        message = f"""
{emoji} **{entry.log_type.value.upper()}**

**User:** `{entry.user_id}`
**Chat:** `{entry.chat_id}`
**Time:** {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
{details_text}
"""
        if entry.message_preview:
            message += f"\n_Message:_ {entry.message_preview}"
        
        try:
            await self.client.send_message(self.log_channel_id, message.strip())
        except Exception as e:
            print(f"Failed to send log to channel: {e}")

    # Convenience methods for common logging
    
    def log_message(self, user_id: int, chat_id: int, message_preview: str):
        """Log a message."""
        return self.log(LogType.MESSAGE, user_id, chat_id, message_preview=message_preview)

    def log_join(self, user_id: int, chat_id: int, username: str = ""):
        """Log a user join."""
        return self.log(LogType.JOIN, user_id, chat_id, details={"username": username})

    def log_leave(self, user_id: int, chat_id: int, username: str = ""):
        """Log a user leave."""
        return self.log(LogType.LEAVE, user_id, chat_id, details={"username": username})

    def log_ban(self, user_id: int, chat_id: int, reason: str, admin_id: int):
        """Log a ban."""
        return self.log(
            LogType.BAN, user_id, chat_id,
            details={"reason": reason, "admin_id": str(admin_id)}
        )

    def log_mute(self, user_id: int, chat_id: int, duration: int, reason: str):
        """Log a mute."""
        return self.log(
            LogType.MUTE, user_id, chat_id,
            details={"duration_seconds": duration, "reason": reason}
        )

    def log_warn(self, user_id: int, chat_id: int, reason: str, warning_number: int):
        """Log a warning."""
        return self.log(
            LogType.WARN, user_id, chat_id,
            details={"reason": reason, "warning_number": warning_number}
        )

    def log_violation(self, user_id: int, chat_id: int, violation_type: str, severity: int):
        """Log a violation."""
        return self.log(
            LogType.VIOLATION, user_id, chat_id,
            details={"violation_type": violation_type, "severity": severity}
        )

    def log_command(self, user_id: int, chat_id: int, command: str):
        """Log a command use."""
        return self.log(
            LogType.COMMAND, user_id, chat_id,
            details={"command": command}
        )

    def log_level_up(self, user_id: int, chat_id: int, old_level: int, new_level: int):
        """Log a level up."""
        return self.log(
            LogType.LEVEL_UP, user_id, chat_id,
            details={"old_level": old_level, "new_level": new_level}
        )

    # Query methods
    
    def get_user_logs(self, user_id: int, limit: int = 50) -> List[LogEntry]:
        """Get logs for a specific user."""
        log_ids = self.user_logs.get(user_id, [])[-limit:]
        return [log for log in self.logs if log.id in log_ids]

    def get_chat_logs(self, chat_id: int, limit: int = 50) -> List[LogEntry]:
        """Get logs for a specific chat."""
        log_ids = self.chat_logs.get(chat_id, [])[-limit:]
        return [log for log in self.logs if log.id in log_ids]

    def get_recent_violations(self, hours: int = 24, limit: int = 100) -> List[LogEntry]:
        """Get recent violations."""
        cutoff = datetime.now().timestamp() - (hours * 3600)
        violations = [
            log for log in self.logs 
            if log.log_type in (LogType.VIOLATION, LogType.WARN, LogType.BAN, LogType.MUTE)
            and log.timestamp.timestamp() > cutoff
        ]
        return violations[-limit:]

    def export_logs(self, format: str = "json") -> str:
        """Export all logs in specified format."""
        if format == "json":
            data = [
                {
                    "id": log.id,
                    "timestamp": log.timestamp.isoformat(),
                    "type": log.log_type.value,
                    "user_id": log.user_id,
                    "chat_id": log.chat_id,
                    "details": log.details,
                    "message_preview": log.message_preview,
                }
                for log in self.logs
            ]
            return json.dumps(data, indent=2)
        elif format == "csv":
            lines = ["id,timestamp,type,user_id,chat_id,details"]
            for log in self.logs:
                lines.append(
                    f'{log.id},{log.timestamp.isoformat()},{log.log_type.value},'
                    f'{log.user_id},{log.chat_id},{json.dumps(log.details)}'
                )
            return "\n".join(lines)
        
        return str(self.logs)
