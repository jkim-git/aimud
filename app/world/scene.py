"""Scene module for the game world."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.character.npc import NPC


@dataclass
class Scene:
    """Represents a scene in the game world.
    
    This is the fundamental building block of our world - each scene represents
    a distinct location with its own description, characters, and interactive elements.
    """
    id: str
    title: str
    description: str
    characters: List[NPC] = field(default_factory=list)
    connections: Dict[str, str] = field(default_factory=dict)  # location_name -> scene_id
    properties: Dict = field(default_factory=dict)
    
    def add_character(self, character: NPC):
        """Add a character to the scene."""
        self.characters.append(character)
        
    def remove_character(self, character_name: str):
        """Remove a character from the scene."""
        self.characters = [c for c in self.characters if c.name != character_name]
        
    def get_character(self, character_name: str) -> Optional[NPC]:
        """Get a character by name."""
        for character in self.characters:
            if character.name == character_name:
                return character
        return None
    
    def add_connection(self, location_name: str, scene_id: str):
        """Add a connection to another scene."""
        self.connections[location_name] = scene_id
        
    def remove_connection(self, location_name: str):
        """Remove a connection."""
        if location_name in self.connections:
            del self.connections[location_name]
        
    def get_connections_description(self) -> str:
        """Get a description of available connections."""
        if not self.connections:
            return "There are no visible paths from here."
        
        conn_desc = "You can go to: "
        conn_list = list(self.connections.keys())
        return conn_desc + ", ".join(conn_list)