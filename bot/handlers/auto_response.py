"""Auto-Response Handler for Custom Commands and Responses."""
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Callable


@dataclass
class AutoResponse:
    """A custom auto-response rule."""
    id: str
    trigger: str  # What triggers this
    response: str  # What to respond with
    trigger_type: str  # "exact", "contains", "regex", "command"
    response_type: str  # "text", "image", "sticker"
    media_url: Optional[str] = None
    button_text: Optional[str] = None
    button_url: Optional[str] = None
    enabled: bool = True
    use_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    is_admin_only: bool = False


class AutoResponseHandler:
    """Handles custom auto-responses and commands."""

    def __init__(self, client=None):
        self.client = client
        
        # Response storage
        self.responses: Dict[str, AutoResponse] = {}  # trigger -> response
        self.response_ids: Dict[str, str] = {}  # id -> trigger
        
        # Default responses (can be customized)
        self._add_defaults()

    def _add_defaults(self):
        """Add some default fun responses."""
        defaults = [
            AutoResponse(
                id="gg",
                trigger="gg",
                response="gg wp! 🎮",
                trigger_type="contains",
                response_type="text"
            ),
            AutoResponse(
                id="gn",
                trigger="gn",
                response="good night! 💤",
                trigger_type="contains",
                response_type="text"
            ),
            AutoResponse(
                id="gm",
                trigger="gm",
                response="good morning! ☀️",
                trigger_type="contains",
                response_type="text"
            ),
            AutoResponse(
                id="sonic",
                trigger="sonic",
                response="🚀 Sonic is the future of DeFi!",
                trigger_type="contains",
                response_type="text"
            ),
            AutoResponse(
                id="lfg",
                trigger="lfg",
                response="LET'S GOOO! 🔥",
                trigger_type="contains",
                response_type="text"
            ),
        ]
        
        for resp in defaults:
            self.add_response(resp)

    def add_response(self, response: AutoResponse):
        """Add or update an auto-response."""
        self.responses[response.trigger.lower()] = response
        self.response_ids[response.id] = response.trigger.lower()

    def remove_response(self, trigger: str) -> bool:
        """Remove an auto-response."""
        trigger = trigger.lower()
        if trigger in self.responses:
            resp = self.responses[trigger]
            del self.response_ids[resp.id]
            del self.responses[trigger]
            return True
        return False

    def get_response(self, trigger: str) -> Optional[AutoResponse]:
        """Get a response by trigger."""
        return self.responses.get(trigger.lower())

    def find_matching_response(self, text: str) -> Optional[AutoResponse]:
        """Find a matching response for text."""
        text_lower = text.lower()
        
        for trigger, response in self.responses.items():
            if not response.enabled:
                continue
                
            if response.trigger_type == "exact":
                if text_lower == trigger:
                    return response
                    
            elif response.trigger_type == "contains":
                if trigger in text_lower:
                    return response
                    
            elif response.trigger_type == "regex":
                try:
                    if re.search(trigger, text_lower):
                        return response
                except:
                    pass
        
        return None

    async def handle_message(self, event) -> bool:
        """Check message for auto-responses. Returns True if response was sent."""
        if not event.text:
            return False
        
        response = self.find_matching_response(event.text)
        
        if not response:
            return False
        
        # Increment use count
        response.use_count += 1
        
        # Send response
        try:
            if response.response_type == "text":
                await event.reply(response.response)
            elif response.response_type == "image" and response.media_url:
                await event.reply(response.response, file=response.media_url)
            elif response.response_type == "sticker" and response.media_url:
                await event.reply(response.media_url)
            
            return True
            
        except Exception as e:
            print(f"Error sending auto-response: {e}")
            return False

    def list_responses(self) -> List[AutoResponse]:
        """List all responses."""
        return list(self.responses.values())

    def get_stats(self) -> dict:
        """Get usage statistics."""
        total_uses = sum(r.use_count for r in self.responses.values())
        enabled_count = sum(1 for r in self.responses.values() if r.enabled)
        
        top_responses = sorted(
            self.responses.values(),
            key=lambda r: r.use_count,
            reverse=True
        )[:5]
        
        return {
            "total_responses": len(self.responses),
            "enabled": enabled_count,
            "total_uses": total_uses,
            "top_responses": [
                {"trigger": r.trigger, "uses": r.use_count}
                for r in top_responses
            ]
        }

    # Admin methods for managing responses
    
    async def add_from_command(self, event, trigger: str, response_text: str, trigger_type: str = "contains"):
        """Add a response from a command."""
        resp = AutoResponse(
            id=f"custom_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            trigger=trigger,
            response=response_text,
            trigger_type=trigger_type,
            response_type="text"
        )
        self.add_response(resp)
        await event.reply(f"✅ Added response: {trigger} → {response_text}")

    async def delete_from_command(self, event, trigger: str):
        """Delete a response from a command."""
        if self.remove_response(trigger):
            await event.reply(f"✅ Deleted response: {trigger}")
        else:
            await event.reply(f"❌ Response not found: {trigger}")

    async def list_from_command(self, event):
        """List all responses from command."""
        responses = self.list_responses()
        
        if not responses:
            await event.reply("No auto-responses configured.")
            return
        
        text = "📝 **Auto-Responses**\n\n"
        for r in responses[:10]:
            status = "✅" if r.enabled else "❌"
            text += f"{status} {r.trigger} → {r.response[:30]}...\n"
        
        if len(responses) > 10:
            text += f"\n_...and {len(responses) - 10} more_"
        
        await event.reply(text, link_preview=False)
