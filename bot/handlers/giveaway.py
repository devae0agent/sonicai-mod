"""Giveaway System for Sonic AI Mod Bot."""
import asyncio
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional


@dataclass
class Giveaway:
    """A giveaway event."""
    id: str
    chat_id: int
    prize: str
    winners_count: int
    ends_at: datetime
    created_by: int
    required_xp: int = 0
    required_level: int = 0
    is_active: bool = True
    participants: List[int] = field(default_factory=list)
    winner_ids: List[int] = field(default_factory=list)
    message_id: Optional[int] = None


class GiveawayHandler:
    """Handles giveaways."""

    def __init__(self, client=None):
        self.client = client
        self.active_giveaways: Dict[int, Giveaway] = {}  # message_id -> giveaway
        self.chat_giveaways: Dict[int, List[Giveaway]] = {}  # chat_id -> giveaways

    async def create_giveaway(
        self,
        chat_id: int,
        prize: str,
        winners_count: int,
        duration_minutes: int,
        created_by: int,
        required_xp: int = 0,
        required_level: int = 0
    ) -> Giveaway:
        """Create a new giveaway."""
        giveaway_id = f"GA-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        giveaway = Giveaway(
            id=giveaway_id,
            chat_id=chat_id,
            prize=prize,
            winners_count=winners_count,
            ends_at=datetime.now() + timedelta(minutes=duration_minutes),
            created_by=created_by,
            required_xp=required_xp,
            required_level=required_level
        )
        
        # Store
        if chat_id not in self.chat_giveaways:
            self.chat_giveaways[chat_id] = []
        self.chat_giveaways[chat_id].append(giveaway)
        
        return giveaway

    async def post_giveaway(self, event, giveaway: Giveaway) -> Optional[message]:
        """Post giveaway to chat."""
        time_left = (giveaway.ends_at - datetime.now()).seconds // 60
        
        text = f"""
🎁 **GIVEAWAY**

**Prize:** {giveaway.prize}

**Winners:** {giveaway.winners_count}
**Ends in:** {time_left} minutes

{'🔒 Required: ' + str(giveaway.required_level) + ' XP' if giveaway.required_xp > 0 else ''}

**To enter:** React with 🎁
"""
        try:
            sent = await event.reply(text.strip())
            giveaway.message_id = sent.id
            self.active_giveaways[sent.id] = giveaway
            
            # Add reaction
            await sent.react("🎁")
            
            return sent
        except Exception as e:
            print(f"Error posting giveaway: {e}")
            return None

    async def add_participant(self, message_id: int, user_id: int, xp_handler) -> bool:
        """Add a participant to a giveaway."""
        if message_id not in self.active_giveaways:
            return False
        
        giveaway = self.active_giveaways[message_id]
        
        # Check if giveaway is active
        if not giveaway.is_active or datetime.now() > giveaway.ends_at:
            return False
        
        # Check if already entered
        if user_id in giveaway.participants:
            return False
        
        # Check XP/level requirements
        if giveaway.required_xp > 0 or giveaway.required_level > 0:
            user_stats = xp_handler.get_user_stats(user_id)
            if user_stats['total_xp'] < giveaway.required_xp:
                return False
            if user_stats['level'] < giveaway.required_level:
                return False
        
        # Add participant
        giveaway.participants.append(user_id)
        return True

    async def end_giveaway(self, message_id: int) -> Optional[List[int]]:
        """End a giveaway and pick winners."""
        if message_id not in self.active_giveaways:
            return None
        
        giveaway = self.active_giveaways[message_id]
        
        if not giveaway.is_active:
            return None
        
        giveaway.is_active = False
        
        # Pick winners
        participants = giveaway.participants
        if len(participants) < giveaway.winners_count:
            # Not enough participants
            giveaway.winner_ids = participants  # All get it
        else:
            giveaway.winner_ids = random.sample(participants, giveaway.winners_count)
        
        return giveaway.winner_ids

    async def announce_winners(self, event, giveaway: Giveaway):
        """Announce winners in chat."""
        if not giveaway.winner_ids:
            text = f"""
🎁 **GIVEAWAY ENDED**

**Prize:** {giveaway.prize}

😕 No winners this time - not enough participants!
"""
        else:
            winners_text = "\n".join(f"• User {w}" for w in giveaway.winner_ids)
            text = f"""
🎁 **GIVEAWAY ENDED**

**Prize:** {giveaway.prize}

🏆 **Winners:**
{winners_text}

Congratulations! 🎉
"""
        
        try:
            await event.reply(text.strip())
        except Exception as e:
            print(f"Error announcing winners: {e}")

    def get_active_giveaways(self, chat_id: int) -> List[Giveaway]:
        """Get active giveaways in a chat."""
        return [
            g for g in self.chat_giveaways.get(chat_id, [])
            if g.is_active and datetime.now() < g.ends_at
        ]

    def get_user_entries(self, user_id: int) -> List[str]:
        """Get all giveaways a user has entered."""
        entries = []
        for giveaway in self.active_giveaways.values():
            if user_id in giveaway.participants:
                entries.append(giveaway.id)
        return entries
