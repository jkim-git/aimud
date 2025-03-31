"""AI Dungeon Master module."""

import json
from typing import Dict, List, Any, Optional

from app.character.npc import NPC
from app.character.player import Player
from app.character.base import Item, Skill
from app.world.scene import Scene
from app.game_engine.state import GameState
from app.utils.llm_utils import (
    call_llm_with_json_response,
    LLMResponseError,
    LLMClientProvider,
    Models
)


class DungeonMaster:
    """AI-powered Dungeon Master.
    
    This is the creative heart of the game - it generates scenarios, 
    scenes, NPCs, and handles the narrative flow based on player actions.
    """
    
    def __init__(self, llm_client_provider: LLMClientProvider):
        """Initialize the Dungeon Master.
        
        Args:
            llm_client_provider: Provider for LLM clients
        """
        # Store the client provider
        self.llm_client_provider = llm_client_provider
        
        # Store the current world state for reference
        self.scenario = {}
        self.scene_memory = {}  # scene_id -> details that aren't in the scene object
        
    def create_scenario(self) -> Dict:
        """Create a new game scenario.
        
        This sets up the initial world, objectives, and narrative framework.
        
        Raises:
            Exception: If there's an API error or parsing error that prevents scenario creation
        """
        # Set up the system prompt for scenario creation
        system_prompt = """
        You are an expert dungeon master creating an immersive text adventure game.
        Create a compelling scenario with:
        1. A rich setting description
        2. A clear mission objective
        3. A basic location layout with named connections between areas
        
        Respond in JSON format with the following structure:
        {
            "title": "Scenario title",
            "setting": "Detailed setting description",
            "objective": "Clear mission objective",
            "environment": "Description of the dungeon/environment",
            "starting_scene_id": "entrance",
            "scenes": {
                "entrance": {
                    "title": "Scene title",
                    "description": "Detailed scene description",
                    "connections": {
                        "Ancient Library": "library",
                        "Dark Passage": "passage",
                        "Grand Hall": "hall"
                    },
                    "characters": [
                        {
                            "name": "Character Name", 
                            "description": "Character description", 
                            "attitude": "neutral",
                            "inventory": [
                                {"name": "Item Name", "description": "Item description"}
                            ],
                            "skills": [
                                {"name": "Skill Name", "description": "Skill description", "cost": "Cost description"}
                            ]
                        }
                    ]
                }
                // Additional scenes
            }
        }
        
        Make it creative, immersive, and suitable for a text-based adventure game.
        
        Key points about connections:
        - Use descriptive location names like "Ancient Library", "Dark Passage", etc.
        - Each connection links to a scene ID that should exist in the scenes object
        - Ensure connections make logical sense - if Scene A connects to Scene B, Scene B should have a connection back to Scene A
        - Include 2-4 connections per scene where appropriate
        """
        
        try:
            # Use CLAUDE_OPUS (best for creative world-building) to generate the scenario
            scenario = call_llm_with_json_response(
                model=Models.CLAUDE_OPUS,
                system_prompt=system_prompt, 
                user_prompt="Create a new adventure scenario.",
                client_provider=self.llm_client_provider,
                response_validator=self._validate_scenario
            )
            
            # Store the scenario for future reference
            self.scenario = scenario
            
            return scenario
            
        except LLMResponseError as e:
            raise Exception(f"Error creating scenario: {str(e)}")
        except Exception as e:
            raise Exception(f"Unexpected error: {str(e)}")
            
    def _validate_scenario(self, scenario: Dict) -> None:
        """Validate a scenario has all required fields.
        
        Args:
            scenario: The scenario data to validate
            
        Raises:
            ValueError: If validation fails
        """
        # Basic validation of required fields
        if "title" not in scenario or "scenes" not in scenario or "starting_scene_id" not in scenario:
            raise ValueError("Missing required fields in scenario")
        
        # Check that starting scene exists in scenes
        if scenario["starting_scene_id"] not in scenario["scenes"]:
            raise ValueError(f"Starting scene ID '{scenario['starting_scene_id']}' not found in scenes")
        
    def setup_player(self, name: str, profile: str) -> Player:
        """Set up the player character based on their profile.
        
        Using the player's name and profile description, generate 
        appropriate inventory and skills.
        
        Args:
            name: The player's name
            profile: The player's character description
            
        Returns:
            Player: A Player object with generated inventory and skills
            
        Raises:
            Exception: If there's an API error or parsing error
        """
        # Set up the system prompt for player character creation
        system_prompt = """
        You are an expert game master helping a player create their character.
        Based on the player's name and profile description, create appropriate
        inventory items and skills.
        
        Respond in JSON format with the following structure:
        {
            "inventory": [
                {"name": "Item Name", "description": "Item description", "properties": {}},
                // Additional items
            ],
            "skills": [
                {"name": "Skill Name", "description": "Skill description", "cost": "Cost description", "properties": {}},
                // Additional skills
            ]
        }
        
        Generate 3-5 inventory items and 3-5 skills that would make sense for the character.
        """
        
        try:
            # Use GPT4 (best for analytical tasks) to generate character details
            character_data = call_llm_with_json_response(
                model=Models.GPT4,
                system_prompt=system_prompt,
                user_prompt=f"Name: {name}\nProfile: {profile}\n\nGenerate appropriate inventory and skills.",
                client_provider=self.llm_client_provider,
                response_validator=self._validate_character_data
            )
            
            # Create inventory items
            inventory = []
            for item_data in character_data["inventory"]:
                item = Item(
                    name=item_data["name"],
                    description=item_data["description"],
                    properties=item_data.get("properties", {})
                )
                inventory.append(item)
                
            # Create skills
            skills = []
            for skill_data in character_data["skills"]:
                skill = Skill(
                    name=skill_data["name"],
                    description=skill_data["description"],
                    cost=skill_data["cost"],
                    properties=skill_data.get("properties", {})
                )
                skills.append(skill)
            
            # Create the player character
            player = Player(
                name=name,
                description=profile,
                inventory=inventory,
                skills=skills
            )
            
            return player
            
        except LLMResponseError as e:
            raise Exception(f"Error creating character: {str(e)}")
        except Exception as e:
            raise Exception(f"Unexpected error: {str(e)}")
            
    def _validate_character_data(self, data: Dict) -> None:
        """Validate character data has all required fields.
        
        Args:
            data: The character data to validate
            
        Raises:
            ValueError: If validation fails
        """
        # Check for required top-level fields
        if "inventory" not in data or "skills" not in data:
            raise ValueError("Missing inventory or skills in character data")
            
        # Validate inventory items
        for i, item in enumerate(data["inventory"]):
            if "name" not in item or "description" not in item:
                raise ValueError(f"Invalid item at index {i}: missing name or description")
                
        # Validate skills
        for i, skill in enumerate(data["skills"]):
            if "name" not in skill or "description" not in skill or "cost" not in skill:
                raise ValueError(f"Invalid skill at index {i}: missing required fields")
        
    def create_scene(self, game_state: GameState, target_scene_id: Optional[str] = None) -> Scene:
        """Create or update a scene based on the current game state.
        
        This generates a new scene or updates an existing one based on the
        current state of the game and the player's actions.
        
        Args:
            game_state: The current game state
            target_scene_id: Optional ID of a scene to generate or retrieve
            
        Returns:
            Scene: The newly created or retrieved scene
        """
        # If we're just starting, create the first scene from the scenario
        if not game_state.current_scene and not target_scene_id:
            starting_scene_id = self.scenario["starting_scene_id"]
            return self._create_scene_from_scenario(starting_scene_id)
            
        # If we have a target scene ID, check if it exists in our scenario
        if target_scene_id:
            # Check if this scene is predefined in our scenario
            if target_scene_id in self.scenario.get("scenes", {}):
                return self._create_scene_from_scenario(target_scene_id)
                
            # Check if we've previously generated this scene
            if target_scene_id in self.scene_memory:
                # Recreate the scene from our memory
                scene_data = self.scene_memory[target_scene_id]
                return self._create_scene_from_data(scene_data)
                
            # If we don't have this scene yet, generate it
            return self._generate_new_scene(game_state, target_scene_id)
            
        # Return the current scene if no specific scene is requested
        if game_state.current_scene:
            return game_state.current_scene
        else:
            raise ValueError("No current scene found")
        
    def _create_scene_from_scenario(self, scene_id: str) -> Scene:
        """Create a scene from the predefined scenario data."""
        scene_data = self.scenario["scenes"][scene_id]
        return self._create_scene_from_data(scene_data, scene_id)
        
    def _create_scene_from_data(self, scene_data: Dict, scene_id: Optional[str] = None) -> Scene:
        """Create a scene from the given data dictionary."""
        if not scene_id:
            scene_id = scene_data.get("id")
            
        # Create NPCs for the scene
        npcs = []
        for char_data in scene_data.get("characters", []):
            # Create inventory items for the NPC
            inventory = []
            for item_data in char_data.get("inventory", []):
                item = Item(
                    name=item_data["name"],
                    description=item_data["description"],
                    properties=item_data.get("properties", {})
                )
                inventory.append(item)
            
            # Create skills for the NPC
            skills = []
            for skill_data in char_data.get("skills", []):
                skill = Skill(
                    name=skill_data["name"],
                    description=skill_data["description"],
                    cost=skill_data["cost"],
                    properties=skill_data.get("properties", {})
                )
                skills.append(skill)
            
            # Create the NPC
            npc = NPC(
                name=char_data["name"],
                description=char_data["description"],
                attitude=char_data.get("attitude", "neutral"),
                inventory=inventory,
                skills=skills
            )
            npcs.append(npc)
        
        # Create the scene
        if not scene_id:
            raise ValueError("Scene ID is required")
        scene = Scene(
            id=scene_id,
            title=scene_data["title"],
            description=scene_data["description"],
            characters=npcs,
            connections=scene_data.get("connections", {})
        )
        
        return scene
        
    def _generate_new_scene(self, game_state: GameState, scene_id: str) -> Scene:
        """Generate a new scene based on the game state and scene_id.
        
        This is used when a player moves to a scene that hasn't been defined yet.
        The AI will create a new scene description, NPCs, and connections.
        """
        # Get the location name used to reach this scene
        location_name = None
        source_scene_id = None
        if game_state.current_scene:
            for loc, sid in game_state.current_scene.connections.items():
                if sid == scene_id:
                    location_name = loc
                    source_scene_id = game_state.current_scene.id
                    break
        
        # Set up context for scene generation
        previous_scene = ""
        if game_state.current_scene:
            previous_scene = f"""
            Previous Scene:
            - Title: {game_state.current_scene.title}
            - Description: {game_state.current_scene.description}
            - ID: {game_state.current_scene.id}
            """
            
        movement_context = ""
        if location_name:
            movement_context = f"The player is going to '{location_name}' from the previous scene."
            
        # Set up the system prompt for scene generation
        system_prompt = """
        You are an expert dungeon master creating a new scene for a text adventure game.
        Based on the current game state and where the player is coming from,
        create a compelling new scene.
        
        Respond in JSON format with the following structure:
        {
            "id": "scene_id",
            "title": "Scene title",
            "description": "Detailed scene description",
            "connections": {
                "Location Name 1": "scene_id1", 
                "Location Name 2": "scene_id2"
            },
            "characters": [
                {
                    "name": "Character Name", 
                    "description": "Character description", 
                    "attitude": "neutral/friendly/hostile",
                    "inventory": [
                        {"name": "Item Name", "description": "Item description"}
                    ],
                    "skills": [
                        {"name": "Skill Name", "description": "Skill description", "cost": "Cost description"}
                    ]
                }
            ]
        }
        
        Make it creative, immersive, and suitable for a text-based adventure game.
        Ensure it fits with the overall scenario and the previous scene.
        
        - The "connections" object maps location names to scene IDs
        - Location names should be descriptive, like "Ancient Library", "Dark Passage", etc.
        - Always include at least one connection back to the previous scene
        - Include 2-4 total connections where appropriate
        """
        
        try:
            # Use CLAUDE_SONNET for creative scene generation
            user_content = f"Scenario: {json.dumps(self.scenario, indent=2)}\n{previous_scene}\n{movement_context}\n\nGenerate a new scene with ID: {scene_id}"
            
            scene_data = call_llm_with_json_response(
                model=Models.CLAUDE_SONNET,
                system_prompt=system_prompt,
                user_prompt=user_content,
                client_provider=self.llm_client_provider,
                response_validator=self._validate_scene_data
            )
            
            # Store the scene data in our memory for future reference
            self.scene_memory[scene_id] = scene_data
            
            # Create the scene
            return self._create_scene_from_data(scene_data, scene_id)
            
        except (json.JSONDecodeError, ValueError, LLMResponseError) as e:
            # Create a simple default scene as fallback
            fallback_scene = {
                "id": scene_id,
                "title": "Mysterious Area",
                "description": "You've arrived at a mysterious area that seems to shift and change before your eyes. The path behind you is clear, but the rest is shrouded in mist.",
                "connections": {},  # Will be populated below
                "characters": []
            }
            
            # Ensure there's a connection back to the previous scene
            if game_state.current_scene:
                back_connection_name = "Path Back"
                fallback_scene["connections"][back_connection_name] = game_state.current_scene.id
                
            return self._create_scene_from_data(fallback_scene, scene_id)
            
        except Exception as e:
            # Simple fallback for other errors
            fallback_scene = {
                "id": scene_id,
                "title": "Unexpected Area",
                "description": "You've arrived at an unexpected area. There seems to be some strange energy interfering with your senses. The path back is clear, but moving forward might be risky.",
                "connections": {},
                "characters": []
            }
            
            # Ensure there's a connection back to the previous scene
            if game_state.current_scene:
                back_connection_name = "Path Back"
                fallback_scene["connections"][back_connection_name] = game_state.current_scene.id
                
            return self._create_scene_from_data(fallback_scene, scene_id)
            
    def _validate_scene_data(self, data: Dict) -> None:
        """Validate scene data has required fields.
        
        Args:
            data: The scene data to validate
            
        Raises:
            ValueError: If validation fails
        """
        if "title" not in data:
            raise ValueError("Missing 'title' field in scene data")
            
        if "description" not in data:
            raise ValueError("Missing 'description' field in scene data")
        
    def resolve_action(self, action: str, game_state: GameState) -> Dict:
        """Resolve a player action and update the game state.
        
        This is where the main game logic happens - interpreting player
        actions and determining their effects on the world.
        
        Args:
            action: The player's action text
            game_state: The current game state
            
        Returns:
            Dict: Action resolution data with state updates
        """
        # Set up the system prompt for action resolution
        system_prompt = """
        You are an expert dungeon master resolving player actions in a text adventure game.
        Based on the player's action, the current scene, and the player's state, determine
        the outcome of the action.
        
        Respond in JSON format with the following structure:
        {
            "success": true/false,
            "description": "Detailed description of what happens",
            "player_updates": {
                "health": "new health status if changed",
                "energy": "new energy status if changed",
                "status": {"status_name": "status_value", "status_to_remove": null},
                "add_items": [{"name": "Item Name", "description": "Item description"}],
                "remove_items": ["Item Name to remove"]
            },
            "character_updates": {
                "Character Name": {
                    "health": "new health status if changed",
                    "energy": "new energy status if changed",
                    "attitude": "new attitude if changed",
                    "add_items": [{"name": "Item Name", "description": "Item description"}],
                    "remove_items": ["Item Name to remove"]
                }
            },
            "scene_updates": {
                "add_characters": [{"name": "NPC Name", "description": "NPC description", "attitude": "neutral"}],
                "remove_characters": ["NPC Name to remove"],
                "new_connections": {"Location Name": "scene_id"}
            },
            "move_to_scene": "scene_id or null",
            "game_over": false,
            "ending_message": "Game over message if game_over is true"
        }
        
        Only include fields that are actually changing. If nothing changes, just include
        success and description.
        
        IMPORTANT: When the player attempts to move to a new location, check if that location
        exists in the current scene's connections. If it does, set move_to_scene to the
        corresponding scene_id. Navigation uses named locations, not directions.
        """
        
        try:
            # Construct the context for the AI including all the relevant game state
            player_context = ""
            if game_state.player:
                player_context = f"""
                Player:
                - Name: {game_state.player.name}
                - Description: {game_state.player.description}
                - Health: {game_state.player.health}
                - Energy: {game_state.player.energy}
                - Status: {json.dumps(game_state.player.status)}
                - Inventory: {json.dumps([{'name': item.name, 'description': item.description} for item in game_state.player.inventory])}
                - Skills: {json.dumps([{'name': skill.name, 'description': skill.description, 'cost': skill.cost} for skill in game_state.player.skills])}
                """
            
            scene_context = ""
            if game_state.current_scene:
                characters_info = []
                for npc in game_state.current_scene.characters:
                    char_info = {
                        'name': npc.name,
                        'description': npc.description,
                        'attitude': npc.attitude,
                        'health': npc.health,
                        'energy': npc.energy,
                        'inventory': [{'name': item.name, 'description': item.description} for item in npc.inventory],
                        'skills': [{'name': skill.name, 'description': skill.description, 'cost': skill.cost} for skill in npc.skills]
                    }
                    characters_info.append(char_info)
                    
                scene_context = f"""
                Current Scene:
                - ID: {game_state.current_scene.id}
                - Title: {game_state.current_scene.title}
                - Description: {game_state.current_scene.description}
                - Characters: {json.dumps(characters_info)}
                - Connections: {json.dumps(game_state.current_scene.connections)}
                """
            
            # Use CLAUDE_SONNET (good balance of creative and efficient) for action resolution
            user_content = f"{player_context}\n{scene_context}\n\nPlayer Action: {action}\n\nResolve this action."
            
            resolution = call_llm_with_json_response(
                model=Models.CLAUDE_SONNET,
                system_prompt=system_prompt,
                user_prompt=user_content,
                client_provider=self.llm_client_provider,
                response_validator=self._validate_action_result
            )
                
            return resolution
            
        except LLMResponseError as e:
            # Create a simple response for parsing errors
            return {
                "success": False,
                "description": f"I'm having trouble understanding what happened. Let's try again. Error: {str(e)}",
                "error": str(e)
            }
        except Exception as e:
            # Create a simple response for API errors
            return {
                "success": False,
                "description": "Something went wrong. Please try your action again.",
                "error": str(e)
            }
    
    def _validate_action_result(self, result: Dict) -> None:
        """Validate action result has required fields.
        
        Args:
            result: The action result to validate
            
        Raises:
            ValueError: If validation fails
        """
        # Check for required fields
        if "success" not in result:
            raise ValueError("Missing 'success' field in action result")
            
        if "description" not in result:
            raise ValueError("Missing 'description' field in action result")