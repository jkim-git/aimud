"""Player character module."""

from dataclasses import dataclass

from app.character.base import Character


@dataclass
class Player(Character):
    """Represents the player character.
    
    The Player class extends the base Character class, inheriting inventory
    and skills. Player-specific features can be added here as needed.
    """
    pass