"""Game state management."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.character.player import Player
from app.character.npc import NPC
from app.world.scene import Scene


@dataclass
class GameState:
    """Represents the current state of the game."""
    player: Optional[Player] = None
    scenario: Dict = field(default_factory=dict)
    current_scene: Optional[Scene] = None
    scene_history: List[Scene] = field(default_factory=list)
    is_game_over: bool = False
    ending_message: str = ""
    
    def update(self, result):
        """Update the game state based on action results."""
        # Update player stats
        if self.player and 'player_updates' in result:
            self.player.update(result['player_updates'])
        
        # Update NPCs in the current scene
        if self.current_scene and 'character_updates' in result:
            for character_name, updates in result['character_updates'].items():
                character = self.current_scene.get_character(character_name)
                if character:
                    character.update(updates)
        
        # Update scene
        if self.current_scene and 'scene_updates' in result:
            scene_updates = result['scene_updates']
            
            # Add new characters
            if 'add_characters' in scene_updates:
                for char_data in scene_updates['add_characters']:
                    npc = NPC(
                        name=char_data['name'],
                        description=char_data['description'],
                        attitude=char_data.get('attitude', 'neutral')
                    )
                    self.current_scene.add_character(npc)
            
            # Remove characters
            if 'remove_characters' in scene_updates:
                for character_name in scene_updates['remove_characters']:
                    self.current_scene.remove_character(character_name)
            
            # Add new connections
            if 'new_connections' in scene_updates:
                for location, scene_id in scene_updates['new_connections'].items():
                    self.current_scene.add_connection(location, scene_id)
        
        # Move to a new scene if specified
        if 'move_to_scene' in result and result['move_to_scene']:
            # We'll add the current scene to history
            if self.current_scene:
                self.scene_history.append(self.current_scene)
            # The actual scene creation happens in the DungeonMaster
        
        # Check for game over condition
        if 'game_over' in result and result['game_over']:
            self.is_game_over = True
            self.ending_message = result.get('ending_message', 'Game Over')