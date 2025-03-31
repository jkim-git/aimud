"""Base character module."""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Item:
    """Represents an item in a character's inventory."""
    name: str
    description: str
    properties: Dict = field(default_factory=dict)


@dataclass
class Skill:
    """Represents a character skill."""
    name: str
    description: str
    cost: str  # Using string to represent cost with more flexibility
    properties: Dict = field(default_factory=dict)


@dataclass
class Character:
    """Base class for all characters in the game."""
    name: str
    description: str
    health: str = "healthy"
    energy: str = "energized"
    status: Dict = field(default_factory=dict)
    inventory: List[Item] = field(default_factory=list)
    skills: List[Skill] = field(default_factory=list)
    
    def update(self, updates):
        """Update character attributes based on action results."""
        if 'health' in updates:
            self.health = updates['health']
            
        if 'energy' in updates:
            self.energy = updates['energy']
            
        if 'status' in updates:
            for key, value in updates['status'].items():
                if value is None and key in self.status:
                    del self.status[key]
                else:
                    self.status[key] = value
                    
        if 'add_items' in updates:
            for item_data in updates['add_items']:
                item = Item(
                    name=item_data['name'],
                    description=item_data['description'],
                    properties=item_data.get('properties', {})
                )
                self.inventory.append(item)
                
        if 'remove_items' in updates:
            for item_name in updates['remove_items']:
                self.inventory = [item for item in self.inventory if item.name != item_name]
    
    @property
    def is_alive(self):
        """Check if the character is alive."""
        return self.health not in ["dead", "deceased", "unconscious"]