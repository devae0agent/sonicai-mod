"""XP and Leveling System for Sonic AI Mod Bot."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class XPEntry:
    """XP earned from an action."""
    amount: int
    action_type: str  # "message", "reaction", "invite", "support"
    timestamp: datetime
    message_preview: str = ""


@dataclass
class LevelReward:
    """A reward unlocked at a certain level."""
    level: int
    name: str
    description: str


class XPHandler:
    """Handles XP and leveling for users."""

    # XP rewards for various actions
    XP_PER_MESSAGE = 1
    XP_PER_REACTION = 1
    XP_PER_INVITE = 10  # When invited user stays for 24h
    XP_PER_SUPPORT_TICKET = 5
    
    # XP thresholds for levels (cumulative)
    LEVEL_THRESHOLDS = {
        1: 0,
        2: 100,
        3: 250,
        4: 500,
        5: 1000,
        6: 1750,
        7: 2750,
        8: 4000,
        9: 5500,
        10: 7500,
        11: 10000,
        12: 13000,
        13: 16500,
        14: 20500,
        15: 25000,
    }
    
    # Level roles/names
    LEVEL_TITLES = {
        1: "New Member",
        2: "Member",
        3: "Regular",
        4: "Contributor",
        5: "Veteran",
        6: "Elite",
        7: "Champion",
        8: "Legend",
        9: "Hero",
        10: "Superstar",
        11: "Master",
        12: "Grandmaster",
        13: "Mythic",
        14: "Eternal",
        15: "GOAT",
    }

    def __init__(self, db=None):
        self.db = db
        self.user_xp: Dict[int, List[XPEntry]] = {}
        self.user_totals: Dict[int, int] = {}
        self.user_levels: Dict[int, int] = {}
        
        # Cooldowns to prevent XP spam
        self.message_cooldowns: Dict[int, datetime] = {}
        self.cooldown_seconds = 60  # Can earn XP once per minute

    def calculate_level(self, total_xp: int) -> int:
        """Calculate level from total XP."""
        level = 1
        for lvl, threshold in sorted(self.LEVEL_THRESHOLDS.items()):
            if total_xp >= threshold:
                level = lvl
            else:
                break
        return level

    def xp_for_next_level(self, current_level: int) -> int:
        """Get XP needed for next level."""
        next_level = current_level + 1
        if next_level not in self.LEVEL_THRESHOLDS:
            return float('inf')  # Max level reached
        
        current_threshold = self.LEVEL_THRESHOLDS.get(current_level, 0)
        return self.LEVEL_THRESHOLDS[next_level] - current_threshold

    def add_xp(self, user_id: int, amount: int, action_type: str, message_preview: str = "") -> Optional[dict]:
        """Add XP to a user. Returns level-up info if leveled up."""
        now = datetime.now()
        
        # Check cooldown for message XP
        if action_type == "message":
            if user_id in self.message_cooldowns:
                if (now - self.message_cooldowns[user_id]).seconds < self.cooldown_seconds:
                    return None  # Still in cooldown
            
            self.message_cooldowns[user_id] = now
        
        # Create XP entry
        entry = XPEntry(
            amount=amount,
            action_type=action_type,
            timestamp=now,
            message_preview=message_preview[:100]
        )
        
        # Add to user's XP history
        if user_id not in self.user_xp:
            self.user_xp[user_id] = []
        self.user_xp[user_id].append(entry)
        
        # Update total
        old_total = self.user_totals.get(user_id, 0)
        new_total = old_total + amount
        self.user_totals[user_id] = new_total
        
        # Calculate new level
        old_level = self.user_levels.get(user_id, 1)
        new_level = self.calculate_level(new_total)
        self.user_levels[user_id] = new_level
        
        # Return level-up info if leveled up
        if new_level > old_level:
            return {
                "old_level": old_level,
                "new_level": new_level,
                "title": self.LEVEL_TITLES.get(new_level, "Member"),
                "xp_needed": self.xp_for_next_level(new_level)
            }
        
        return None

    def get_user_stats(self, user_id: int) -> dict:
        """Get comprehensive stats for a user."""
        total_xp = self.user_totals.get(user_id, 0)
        level = self.user_levels.get(user_id, 1)
        
        # Count actions by type
        if user_id in self.user_xp:
            actions = self.user_xp[user_id]
            message_count = sum(1 for a in actions if a.action_type == "message")
            reaction_count = sum(1 for a in actions if a.action_type == "reaction")
            invite_count = sum(1 for a in actions if a.action_type == "invite")
        else:
            message_count = reaction_count = invite_count = 0
        
        xp_to_next = self.xp_for_next_level(level)
        progress = 0
        if xp_to_next != float('inf'):
            current_level_xp = self.LEVEL_THRESHOLDS.get(level, 0)
            progress = ((total_xp - current_level_xp) / xp_to_next) * 100
        
        return {
            "user_id": user_id,
            "total_xp": total_xp,
            "level": level,
            "title": self.LEVEL_TITLES.get(level, "Member"),
            "xp_to_next": xp_to_next,
            "progress": progress,
            "message_count": message_count,
            "reaction_count": reaction_count,
            "invite_count": invite_count,
        }

    def get_leaderboard(self, limit: int = 10) -> List[dict]:
        """Get top users by XP."""
        sorted_users = sorted(
            self.user_totals.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        leaderboard = []
        for rank, (user_id, xp) in enumerate(sorted_users[:limit], 1):
            level = self.user_levels.get(user_id, 1)
            leaderboard.append({
                "rank": rank,
                "user_id": user_id,
                "xp": xp,
                "level": level,
                "title": self.LEVEL_TITLES.get(level, "Member")
            })
        
        return leaderboard

    async def reward_invite(self, user_id: int):
        """Reward user for successful invite."""
        return self.add_xp(user_id, self.XP_PER_INVITE, "invite")

    async def reward_message(self, user_id: int, message_preview: str = ""):
        """Reward user for sending a message."""
        return self.add_xp(user_id, self.XP_PER_MESSAGE, "message", message_preview)

    async def reward_reaction(self, user_id: int):
        """Reward user for reacting to a message."""
        return self.add_xp(user_id, self.XP_PER_REACTION, "reaction")
