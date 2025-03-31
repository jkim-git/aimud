"""Utility functions for interacting with LLMs."""

import json
from enum import Enum, auto
from dataclasses import dataclass
from typing import Dict, Any, Callable, Optional

from app.utils.debug import debug_print


class LLMProvider(Enum):
    """Enum for different LLM providers."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


class ModelType(Enum):
    """Model types for different purposes."""
    CREATIVE = auto()  # For creative and narrative-rich content
    ANALYTICAL = auto()  # For structured, analytical content
    EFFICIENT = auto()  # For quick, simple responses


@dataclass
class ModelCard:
    """Configuration for a specific LLM model."""
    name: str  # API name of the model
    provider: LLMProvider  # Which provider this belongs to
    type: ModelType  # What this model is best suited for
    max_tokens: int = 4000  # Default token limit
    temperature: float = 0.7  # Default temperature


class Models(Enum):
    """Available models with their configurations."""
    CLAUDE_OPUS = ModelCard(
        name="claude-3-opus-20240229", 
        provider=LLMProvider.ANTHROPIC, 
        type=ModelType.CREATIVE,
        max_tokens=4000
    )
    CLAUDE_SONNET = ModelCard(
        name="claude-3-sonnet-20240229", 
        provider=LLMProvider.ANTHROPIC, 
        type=ModelType.CREATIVE,
        max_tokens=2000
    )
    GPT4 = ModelCard(
        name="gpt-4", 
        provider=LLMProvider.OPENAI, 
        type=ModelType.ANALYTICAL
    )
    GPT35_TURBO = ModelCard(
        name="gpt-3.5-turbo", 
        provider=LLMProvider.OPENAI, 
        type=ModelType.EFFICIENT
    )


class LLMClientProvider:
    """Provider for LLM clients."""
    
    def __init__(self, anthropic_client=None, openai_client=None):
        """Initialize with specific clients.
        
        Args:
            anthropic_client: Anthropic API client
            openai_client: OpenAI API client
        """
        self.clients = {
            LLMProvider.ANTHROPIC: anthropic_client,
            LLMProvider.OPENAI: openai_client
        }
    
    def get_client(self, provider: LLMProvider) -> Any:
        """Get the client for a specific provider.
        
        Args:
            provider: The LLM provider enum
            
        Returns:
            The client for the specified provider
            
        Raises:
            ValueError: If the client is not available
        """
        client = self.clients.get(provider)
        if not client:
            raise ValueError(f"Client for {provider.value} is not available")
        return client


class LLMResponseError(Exception):
    """Exception raised when there's an issue with an LLM response."""
    pass


def call_llm_with_json_response(
    model: Models,
    system_prompt: str,
    user_prompt: str,
    client_provider: LLMClientProvider,
    response_validator: Optional[Callable[[Dict], None]] = None
) -> Dict:
    """Make a call to an LLM and parse the JSON response.
    
    Args:
        model: The model to use (from Models enum)
        system_prompt: The system prompt to send
        user_prompt: The user prompt to send
        client_provider: Provider for LLM clients
        response_validator: Optional function to validate the response structure
        
    Returns:
        Dict: The parsed JSON response
        
    Raises:
        LLMResponseError: If there's an issue with the response or parsing
    """
    try:
        # Get model card details
        model_card = model.value
        provider = model_card.provider
        
        debug_print(f"Making API call to {provider.value} using model {model_card.name}")
        debug_print(f"System prompt preview: {system_prompt[:100]}...")
        debug_print(f"User prompt preview: {user_prompt[:100]}...")
        
        # Get the appropriate client
        client = client_provider.get_client(provider)
        
        # Make the API call based on provider
        if provider == LLMProvider.ANTHROPIC:
            debug_print("Calling Anthropic API...")
            response = client.messages.create(
                model=model_card.name,
                max_tokens=model_card.max_tokens,
                temperature=model_card.temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            response_text = response.content[0].text
            
        elif provider == LLMProvider.OPENAI:
            debug_print("Calling OpenAI API...")
            response = client.chat.completions.create(
                model=model_card.name,
                temperature=model_card.temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            response_text = response.choices[0].message.content
            
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
        
        debug_print(f"Received response ({len(response_text)} chars)")
        debug_print(f"Response preview: {response_text[:100]}...")
        
        # Parse the JSON from the response
        json_data = extract_json(response_text)
        debug_print(f"JSON parsed successfully. Keys: {list(json_data.keys())}")
        
        # Validate the response if a validator was provided
        if response_validator:
            debug_print("Validating response...")
            response_validator(json_data)
            debug_print("Response validation successful")
            
        return json_data
    
    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse JSON response: {str(e)}"
        debug_print(f"ERROR: {error_msg}")
        raise LLMResponseError(error_msg)
    except Exception as e:
        error_msg = f"Error making LLM call: {str(e)}"
        debug_print(f"ERROR: {error_msg}")
        raise LLMResponseError(error_msg)


def extract_json(text: str) -> Dict:
    """Extract JSON from text that might contain markdown code blocks.
    
    Args:
        text: The text containing JSON
        
    Returns:
        Dict: The parsed JSON data
        
    Raises:
        json.JSONDecodeError: If JSON parsing fails
    """
    debug_print("Extracting JSON from response...")
    
    # Extract JSON from markdown code blocks if present
    json_text = text
    
    if "```json" in text.lower():
        debug_print("Found ```json code block marker")
        # Handle ```json code blocks
        parts = text.split("```json", 1)[1].split("```", 1)
        if parts:
            json_text = parts[0]
            debug_print("Extracted content from ```json block")
    elif "```" in text:
        debug_print("Found ``` code block marker")
        # Handle plain ``` code blocks
        parts = text.split("```", 1)[1].split("```", 1)
        if parts:
            json_text = parts[0]
            debug_print("Extracted content from ``` block")
    
    # Try to find something that looks like JSON by searching for outermost braces
    if "{" in json_text and "}" in json_text:
        # Find the first opening brace and last closing brace
        start = json_text.find("{")
        end = json_text.rfind("}") + 1
        json_text = json_text[start:end]
        debug_print(f"Isolated JSON object from char {start} to {end}")
    
    # Parse the JSON
    try:
        debug_print("Attempting to parse JSON...")
        result = json.loads(json_text.strip())
        debug_print("JSON parsed successfully")
        return result
    except json.JSONDecodeError as e:
        debug_print(f"JSON parsing failed: {str(e)}")
        debug_print("Attempting fallback parsing method...")
        # Try a more aggressive approach - find just the JSON object
        import re
        match = re.search(r'\{.*\}', json_text, re.DOTALL)
        if match:
            debug_print("Found JSON-like pattern with regex")
            try:
                result = json.loads(match.group(0))
                debug_print("Fallback parsing successful")
                return result
            except json.JSONDecodeError as e2:
                debug_print(f"Fallback parsing also failed: {str(e2)}")
        debug_print("All parsing attempts failed")
        raise