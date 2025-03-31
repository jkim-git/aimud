"""Core game engine that manages the game loop and flow."""

from typing import Optional
from rich.console import Console
from rich.panel import Panel

from app.game_engine.state import GameState
from app.ai.dungeon_master import DungeonMaster

class GameEngine:
    """Main game engine that controls game flow."""
    
    def __init__(self, dungeon_master: DungeonMaster):
        """Initialize the game engine."""
        self.state = GameState()
        self.dm = dungeon_master
        self.console = Console()
        
    def setup_game(self):
        """Setup the initial game scenario."""
        # DM creates scenario
        scenario = self.dm.create_scenario()
        self.state.scenario = scenario
        
        # Get player information
        self.setup_player()
        
        return scenario
    
    def setup_player(self, name: Optional[str] = None, profile: Optional[str] = None):
        """Set up the player character."""
        if not name or not profile:
            return
            
        # Create player using the DM
        player = self.dm.setup_player(name, profile)
        self.state.player = player
        
    def display_scene(self, scene):
        """Display the current scene to the player."""
        # Create a panel for the scene
        self.console.print(Panel.fit(
            f"[bold cyan]{scene.title}[/bold cyan]\n\n"
            f"{scene.description}\n",
            border_style="cyan"
        ))
        
        # Display available connections
        if scene.connections:
            connection_list = ", ".join([f"[cyan]{location}[/cyan]" for location in scene.connections.keys()])
            self.console.print(f"[bold green]You can go to:[/bold green] {connection_list}")
        else:
            self.console.print("[bold red]There are no visible paths from here.[/bold red]")
        
        # Display characters in the scene
        if scene.characters:
            self.console.print("\n[bold yellow]Characters present:[/bold yellow]")
            for character in scene.characters:
                attitude_color = "green" if character.attitude == "friendly" else "yellow" if character.attitude == "neutral" else "red"
                self.console.print(f"- {character.name} ([{attitude_color}]{character.attitude}[/{attitude_color}])")
    
    def start_gameplay(self):
        """Start the main gameplay loop."""
        # Generate first scene
        current_scene = self.dm.create_scene(self.state)
        self.state.current_scene = current_scene
        
        # Main gameplay loop
        while not self.state.is_game_over:
            # Display current scene
            self.display_scene(current_scene)
            
            # Get player action
            action = input("\n> ")
            
            # Process player action
            try:
                result = self.dm.resolve_action(action, self.state)
                
                # Display the action result description
                if "description" in result:
                    self.console.print(f"\n{result['description']}")
                
                # Check if we need to move to a new scene
                target_scene_id = result.get("move_to_scene")
                
                # Update game state
                self.state.update(result)
                
                # Generate next scene if we're moving
                if target_scene_id:
                    current_scene = self.dm.create_scene(self.state, target_scene_id)
                    self.state.current_scene = current_scene
                
            except Exception as e:
                self.console.print(f"[bold red]Error processing action: {str(e)}[/bold red]")
                self.console.print("Please try a different action.")
            
        # Game over
        self.console.print(Panel.fit(
            f"[bold red]Game Over[/bold red]\n\n"
            f"{self.state.ending_message}",
            border_style="red"
        ))
        
    def display_player_status(self):
        """Display the player's current status."""
        if not self.state.player:
            return
            
        player = self.state.player
        
        # Create health color based on status
        health_color = "green"
        if player.health in ["wounded", "injured", "hurt"]:
            health_color = "yellow"
        elif player.health in ["critical", "dying", "near death"]:
            health_color = "red"
            
        # Create energy color based on status
        energy_color = "green"
        if player.energy in ["tired", "fatigued"]:
            energy_color = "yellow"
        elif player.energy in ["exhausted", "depleted"]:
            energy_color = "red"
        
        # Display player status
        self.console.print(Panel.fit(
            f"[bold]{player.name}[/bold]\n\n"
            f"Health: [{health_color}]{player.health}[/{health_color}]\n"
            f"Energy: [{energy_color}]{player.energy}[/{energy_color}]\n"
            + (f"Status: {', '.join(f'[yellow]{k}[/yellow]' for k in player.status.keys())}\n" if player.status else ""),
            title="Status",
            border_style="blue"
        ))
        
    def display_inventory(self):
        """Display the player's inventory."""
        if not self.state.player:
            return
            
        player = self.state.player
        
        if not player.inventory:
            self.console.print("[yellow]Your inventory is empty.[/yellow]")
            return
            
        inventory_text = "\n".join([f"- [cyan]{item.name}[/cyan]: {item.description}" for item in player.inventory])
        
        self.console.print(Panel.fit(
            inventory_text,
            title="Inventory",
            border_style="cyan"
        ))
        
    def display_skills(self):
        """Display the player's skills."""
        if not self.state.player:
            return
            
        player = self.state.player
        
        if not player.skills:
            self.console.print("[yellow]You don't have any skills yet.[/yellow]")
            return
            
        skills_text = "\n".join([f"- [magenta]{skill.name}[/magenta]: {skill.description} (Cost: {skill.cost})" for skill in player.skills])
        
        self.console.print(Panel.fit(
            skills_text,
            title="Skills",
            border_style="magenta"
        ))