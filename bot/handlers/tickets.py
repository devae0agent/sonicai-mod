"""Ticket Integration Handler for Sonic AI Mod Bot."""
import asyncio
import httpx
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class TicketConfig:
    """Configuration for ticket integration."""
    enabled: bool = True
    n8n_webhook_url: Optional[str] = None
    ticket_channel_id: Optional[int] = None
    max_open_tickets: int = 3
    cooldown_minutes: int = 60


@dataclass
class Ticket:
    """A support ticket."""
    id: str
    user_id: int
    chat_id: int
    created_at: datetime
    status: str  # "open", "pending", "closed"
    subject: str
    description: str


class TicketHandler:
    """Handles support ticket creation and management."""

    def __init__(self, client=None, config: TicketConfig = None):
        self.client = client
        self.config = config or TicketConfig()
        
        # In-memory ticket tracking
        self.user_tickets: Dict[int, List[Ticket]] = {}
        self.open_tickets: Dict[str, Ticket] = {}  # ticket_id -> ticket
        
        # Cooldown tracking
        self.user_last_ticket: Dict[int, datetime] = {}

    async def create_ticket(
        self,
        user_id: int,
        chat_id: int,
        subject: str,
        description: str
    ) -> Optional[Ticket]:
        """Create a new support ticket."""
        
        # Check cooldown
        if user_id in self.user_last_ticket:
            time_since = (datetime.now() - self.user_last_ticket[user_id]).seconds
            cooldown_seconds = self.config.cooldown_minutes * 60
            
            if time_since < cooldown_seconds:
                remaining = (cooldown_seconds - time_since) // 60
                return None  # Still in cooldown
        
        # Check max open tickets
        user_open = len([
            t for t in self.user_tickets.get(user_id, [])
            if t.status == "open"
        ])
        
        if user_open >= self.config.max_open_tickets:
            return None  # Too many open tickets
        
        # Generate ticket ID
        ticket_id = f"TICKET-{datetime.now().strftime('%Y%m%d%H%M%S')}-{user_id % 10000}"
        
        # Create ticket
        ticket = Ticket(
            id=ticket_id,
            user_id=user_id,
            chat_id=chat_id,
            created_at=datetime.now(),
            status="open",
            subject=subject,
            description=description
        )
        
        # Store ticket
        if user_id not in self.user_tickets:
            self.user_tickets[user_id] = []
        self.user_tickets[user_id].append(ticket)
        self.open_tickets[ticket_id] = ticket
        
        # Update cooldown
        self.user_last_ticket[user_id] = datetime.now()
        
        # Send to n8n webhook if configured
        if self.config.n8n_webhook_url:
            asyncio.create_task(self._send_to_n8n(ticket))
        
        # Notify in chat if configured
        if self.config.ticket_channel_id:
            asyncio.create_task(self._notify_channel(ticket))
        
        return ticket

    async def _send_to_n8n(self, ticket: Ticket):
        """Send ticket data to n8n webhook."""
        if not self.config.n8n_webhook_url:
            return
        
        payload = {
            "ticket_id": ticket.id,
            "user_id": ticket.user_id,
            "chat_id": ticket.chat_id,
            "subject": ticket.subject,
            "description": ticket.description,
            "created_at": ticket.created_at.isoformat(),
            "source": "telegram_mod_bot"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    self.config.n8n_webhook_url,
                    json=payload,
                    timeout=10.0
                )
        except Exception as e:
            print(f"Failed to send ticket to n8n: {e}")

    async def _notify_channel(self, ticket: Ticket):
        """Notify ticket channel of new ticket."""
        if not self.client or not self.config.ticket_channel_id:
            return
        
        message = f"""
🎫 **New Ticket Created**

**ID:** `{ticket.id}`
**User:** `{ticket.user_id}`
**Subject:** {ticket.subject}

_Description:_
{ticket.description}
"""
        try:
            await self.client.send_message(
                self.config.ticket_channel_id,
                message.strip()
            )
        except Exception as e:
            print(f"Failed to notify ticket channel: {e}")

    async def close_ticket(self, ticket_id: str) -> bool:
        """Close a ticket."""
        if ticket_id not in self.open_tickets:
            return False
        
        ticket = self.open_tickets[ticket_id]
        ticket.status = "closed"
        del self.open_tickets[ticket_id]
        
        return True

    def get_user_tickets(self, user_id: int) -> List[Ticket]:
        """Get all tickets for a user."""
        return self.user_tickets.get(user_id, [])

    def get_open_ticket(self, user_id: int) -> Optional[Ticket]:
        """Get the first open ticket for a user."""
        for ticket in self.user_tickets.get(user_id, []):
            if ticket.status == "open":
                return ticket
        return None

    def get_all_open_tickets(self) -> List[Ticket]:
        """Get all open tickets."""
        return list(self.open_tickets.values())

    def set_webhook_url(self, url: str):
        """Set the n8n webhook URL."""
        self.config.n8n_webhook_url = url

    def set_ticket_channel(self, channel_id: int):
        """Set the ticket notification channel."""
        self.config.ticket_channel_id = channel_id
