"""
Base implementation for LLM service 
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel

class LLMClient(ABC):
    """Abstract base class for LLM clients.
    
    This class defines the interface that all LLM clients must implement.
    """
    
    def __init__(self, **kwargs):
        """Initialize the LLM client.
        
        Args:
            **kwargs: Additional configuration options
        """
        self.config = kwargs
    
    @abstractmethod
    def generate(self, system_prompt: Optional[str] , user_prompt: str, **kwargs) -> BaseModel:
        """Generate text based on the prompt.
        
        Args:
            system_prompt: Optional system  prompt
            user_prompt: user prompt
            images: Image input for vision enabled models 
            **kwargs: Additional generation parameters
            
        Returns:
            Generated response structure
        """
        pass

    @abstractmethod
    def generate_structured_response(self, system_prompt: Optional[str], user_prompt:str, structure, **kwargs)->BaseModel:
        """Generate structured reponse based on the chat messages history.

        Args:
            system_prompt: Optional system  prompt
            user_prompt: user prompt
            structure: structure for response
            **kwargs: Additional generation parameters
            
        Returns:
            Generated response structure 
        """
        pass