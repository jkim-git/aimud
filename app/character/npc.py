"""Non-player character module."""

from dataclasses import dataclass, field
from typing import Dict

from app.character.base import Character


@dataclass
class NPC(Character):
    """Represents a non-player character."""
    attitude: str = "neutral"  # friendly, neutral, hostile, etc.
    properties: Dict = field(default_factory=dict)
    
    def update(self, updates):
        """Update NPC attributes based on action results."""
        super().update(updates)
            
        if 'attitude' in updates:
            self.attitude = updates['attitude']
                    
        if 'properties' in updates:
            for key, value in updates['properties'].items():
                if value is None and key in self.properties:
                    del self.properties[key]
                else:
                    self.properties[key] = value