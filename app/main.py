"""Main entry point for the AIMUD game."""

import os
import sys
import traceback
import argparse
import anthropic
import openai
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from app.game_engine.engine import GameEngine
from app.ai.dungeon_master import DungeonMaster
from app.utils.llm_utils import LLMClientProvider
from app.utils.debug import debug_print


def check_environment():
    """Check if required environment variables are set."""
    missing_vars = []
    
    load_dotenv()
    
    if not os.getenv("OPENAI_API_KEY"):
        missing_vars.append("OPENAI_API_KEY")
        
    if not os.getenv("ANTHROPIC_API_KEY"):
        missing_vars.append("ANTHROPIC_API_KEY")
        
    if missing_vars:
        print("Error: The following environment variables are required but not set:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease set these environment variables and try again.")
        sys.exit(1)


def create_llm_client_provider():
    """Create and initialize the LLM client provider.
    
    Returns:
        LLMClientProvider: Initialized provider with LLM clients
    """
    debug_print("Initializing LLM clients...")
    
    # Initialize API clients
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    debug_print(f"Anthropic API key present: {bool(anthropic_api_key)}")
    debug_print(f"OpenAI API key present: {bool(openai_api_key)}")
    
    anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
    openai_client = openai.OpenAI(api_key=openai_api_key)
    
    debug_print("LLM clients initialized successfully")
    
    # Create and return the client provider
    return LLMClientProvider(
        anthropic_client=anthropic_client,
        openai_client=openai_client
    )


def display_help(console):
    """Display help information."""
    help_table = Table(title="AIMUD Commands")
    help_table.add_column("Command", style="cyan")
    help_table.add_column("Description", style="green")
    
    # Add special commands
    console.print("[bold]Special Commands:[/bold]")
    help_table.add_row("/help", "Display this help message")
    help_table.add_row("/status", "Display your character's status")
    help_table.add_row("/inventory", "Display your inventory")
    help_table.add_row("/skills", "Display your skills")
    help_table.add_row("/connections", "Display available connections")
    help_table.add_row("/look", "Look around the current scene")
    help_table.add_row("/quit", "Exit the game")
    console.print(help_table)
    
    # Add natural language examples
    example_table = Table(title="Natural Language Examples")
    example_table.add_column("Command", style="cyan")
    example_table.add_column("Effect", style="green")
    
    example_table.add_row("go to Ancient Library", "Move to the Ancient Library location")
    example_table.add_row("examine the artifact", "Look at an object more closely")
    example_table.add_row("talk to the guard", "Start a conversation")
    example_table.add_row("use healing potion", "Use an item from your inventory")
    example_table.add_row("attack the goblin", "Initiate combat")
    console.print(example_table)
    
    console.print("\n[italic]The AI understands natural language, so feel free to express commands in your own words.[/italic]")


def custom_input(prompt=""):
    """Custom input function that handles special commands."""
    while True:
        user_input = input(prompt).strip()
        
        # Handle empty input
        if not user_input:
            print("Please enter a command.")
            continue
            
        return user_input


def main():
    """Run the game."""
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description="AIMUD - AI-powered Multi-User Dungeon")
        parser.add_argument("--debug", action="store_true", help="Enable debug output")
        args = parser.parse_args()
        
        # Set debug mode (via environment in debug.py)
        if args.debug:
            os.environ["DEBUG"] = "1"
            
        # Load environment variables from .env file if it exists
        load_dotenv()
        
        # Check environment
        check_environment()
        
        debug_print("Debug mode enabled")
        debug_print("Environment checked OK")
        
        # Create console for rich text output
        console = Console()
        
        # Display welcome message
        console.print(Panel.fit(
            "[bold cyan]Welcome to AIMUD![/bold cyan]\n\n"
            "An AI-powered Multi-User Dungeon experience.",
            title="AIMUD",
            border_style="cyan"
        ))
        
        # Create shared LLM client provider
        llm_client_provider = create_llm_client_provider()
        
        # Initialize the game engine and dungeon master with shared client provider
        dm = DungeonMaster(llm_client_provider=llm_client_provider)
        engine = GameEngine(dungeon_master=dm)

        # Setup the game scenario
        console.print("\n[bold green]Setting up the adventure...[/bold green]")
        scenario = engine.setup_game()
        
        # Display scenario information
        console.print(Panel.fit(
            f"[bold]{scenario['title']}[/bold]\n\n"
            f"{scenario['setting']}\n\n"
            f"[bold]Your Mission:[/bold] {scenario['objective']}",
            title="Adventure",
            border_style="green"
        ))
        
        # Get player information
        console.print("\n[bold blue]Character Creation[/bold blue]")
        player_name = custom_input("What is your name? ")
        player_profile = custom_input("Describe your character: ")
        
        # Create player
        player = dm.setup_player(player_name, player_profile)
        engine.state.player = player
        
        # Display player information
        console.print(Panel.fit(
            f"[bold]{player.name}[/bold]\n"
            f"{player.description}\n\n"
            f"[bold]Health:[/bold] {player.health}\n"
            f"[bold]Energy:[/bold] {player.energy}\n\n"
            "[bold]Inventory:[/bold]"
            + ''.join([f"\n- {item.name}: {item.description}" for item in player.inventory])
            + "\n\n[bold]Skills:[/bold]"
            + ''.join([f"\n- {skill.name}: {skill.description} (Cost: {skill.cost})" for skill in player.skills]),
            title="Character",
            border_style="blue"
        ))
        
        # Display help information
        console.print("\n[bold yellow]Type /help at any time to see available commands.[/bold yellow]")
        
        # Start the game
        console.print("\n[bold magenta]Let the adventure begin![/bold magenta]")
        
        # Main game loop
        current_scene = dm.create_scene(engine.state)
        engine.state.current_scene = current_scene
        
        # Game loop with special command handling
        while not engine.state.is_game_over:
            # Display current scene
            engine.display_scene(current_scene)
            
            # Get player action
            action = custom_input("\n> ")
            
            # Handle special commands
            if action.startswith("/"):
                command = action[1:].lower()
                
                if command == "help":
                    display_help(console)
                    continue
                    
                elif command == "status":
                    engine.display_player_status()
                    continue
                    
                elif command == "inventory":
                    engine.display_inventory()
                    continue
                    
                elif command == "skills":
                    engine.display_skills()
                    continue
                    
                elif command == "connections":
                    if current_scene.connections:
                        connection_list = ", ".join([f"[cyan]{location}[/cyan]" for location in current_scene.connections.keys()])
                        console.print(f"[bold green]You can go to:[/bold green] {connection_list}")
                    else:
                        console.print("[bold red]There are no visible paths from here.[/bold red]")
                    continue
                    
                elif command == "look":
                    engine.display_scene(current_scene)
                    continue
                    
                elif command == "quit":
                    if console.input("[bold red]Are you sure you want to quit? (y/n)[/bold red] ").lower() == "y":
                        console.print("[bold cyan]Thanks for playing AIMUD![/bold cyan]")
                        return
                    continue
                    
                else:
                    console.print(f"[bold red]Unknown command: {action}[/bold red]")
                    console.print("Type /help to see available commands.")
                    continue
            
            # Process regular player action with the AI
            try:
                result = dm.resolve_action(action, engine.state)
                
                # Display the action result description
                if "description" in result:
                    console.print(f"\n{result['description']}")
                
                # Check if we need to move to a new scene
                target_scene_id = result.get("move_to_scene")
                
                # Update game state
                engine.state.update(result)
                
                # Generate next scene if we're moving
                if target_scene_id:
                    current_scene = dm.create_scene(engine.state, target_scene_id)
                    engine.state.current_scene = current_scene
                
            except Exception as e:
                console.print(f"[bold red]Error processing action: {str(e)}[/bold red]")
                console.print("Please try a different action.")
        
        # Game over
        console.print(Panel.fit(
            f"[bold red]Game Over[/bold red]\n\n"
            f"{engine.state.ending_message}",
            border_style="red"
        ))
        
    except KeyboardInterrupt:
        console = Console()
        console.print("\n[bold cyan]Game interrupted. Thanks for playing AIMUD![/bold cyan]")
        
    except Exception as e:
        console = Console()
        console.print(f"[bold red]An unexpected error occurred:[/bold red]")
        console.print(f"{str(e)}")
        console.print("\nPlease report this issue with the following details:")
        console.print(traceback.format_exc())
    
    
if __name__ == "__main__":
    main()