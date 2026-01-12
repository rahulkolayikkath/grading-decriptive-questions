"""
Client implementation for Google's Gemini models .

"""
import os
from typing import Dict, List, Optional, Union, Any, Generator
import logging
from .base import LLMClient
from pydantic import BaseModel
import requests
import base64
import json
from google import genai
from google.genai import types
from config import models

logger = logging.getLogger(__name__)

#pydantic models for query and response
class GeminiResponse(BaseModel):
    content : Optional[str] = None
    input_tokens: float
    output_tokens: float
    model: str 
    cost: float
    success: bool = True
    error_message: Optional[str] = None

class GeminiStructuredResponse(BaseModel):
    structure: Optional[dict] = None
    input_tokens: float
    output_tokens: float
    model: str
    cost: float
    success: bool = True
    error_message: Optional[str] = None

class GeminiClient(LLMClient):
    """Client for interacting with Gemini modesl through Google AI studio API."""
    
    def __init__(self,
                 api_key: Optional[str] = None, 
                 model: str = "gemini-2.0-flash",
                ):
        """Initialize the Gemini client.
        
        Args:
            model: Model to use (default is gemini-2.0-flash)
        """
        api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("The api key must be provided either as an argument or via environment variable")
        
        super().__init__()
        self.model = model
        self.client = genai.Client(api_key=api_key)

    def generate(self, 
                 user_prompt: str,
                 system_prompt: Optional[str]= None,
                 images: List= [],
                 max_tokens: int = 4048,
                 temperature: float = 0.1,
                ) -> GeminiResponse:
        """Generate text using Gemini.
        
        Args:
            prompt: The user prompt to send to Gemini
            images: Images for context
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature (0.0 to 1.0)
            system_prompt: Optional system prompt to guide Gemini's behavior
            
        Returns:
            Generated response structure
        """
        try:
            # add images in context if any 
            image_content = []
            for image in images:
                image_bytes = requests.get(image).content
                image = types.Part.from_bytes(
                data=image_bytes, mime_type="image/jpeg"
                )
                image_content.append(image)
            
            # prepare config for thinking and non thinking
            # Gemini2.5 pro only operates in thinking mode(cant put budget as zero)
            if self.model == "gemini-2.0-flash" or self.model  == "gemini-2.5-pro":
                model_config = types.GenerateContentConfig(
                    system_instruction = system_prompt,
                    max_output_tokens=max_tokens,
                    temperature= temperature
                    )
            # thinking of flash can be restricted 
            elif self.model == "gemini-2.5-flash":
                model_config = types.GenerateContentConfig(
                    system_instruction = system_prompt,
                    max_output_tokens=max_tokens,
                    temperature= temperature,
                    thinking_config=types.ThinkingConfig(thinking_budget=0)
                    )
            
            response = self.client.models.generate_content(
                model = self.model,
                config = model_config,
                contents =  image_content+[user_prompt],#recommened image before the prompt
            )
            
            # Check that the response has a `text` field
            text = getattr(response, "text", None)
            if text is None:
                raise ValueError("Gemini response did not contain text output.")
            
            input_tok = response.usage_metadata.prompt_token_count
            output_tok = response.usage_metadata.total_token_count - response.usage_metadata.prompt_token_count
            
            cost  = input_tok* (models[self.model]['input_cost']/1000000) + output_tok * (models[self.model]['output_cost']/1000000)
            
            return GeminiResponse(
                content = response.text,
                input_tokens = input_tok,
                output_tokens = output_tok,
                cost = cost,
                model= self.model,
                success=True
                )
            
        except Exception as e:
            logger.error(f"Error generating text with Gemini from Google AI studio: {str(e)}")
            return GeminiResponse(
                content = None,
                input_tokens = 0,
                output_tokens = 0,
                cost = 0.0,
                model= self.model,
                success=False,
                error_message= f"Error generating text with Gemini from Google AI studio: {str(e)}"
                )

    def generate_structured_response(self, 
                                     user_prompt:str,
                                     structure,
                                     system_prompt: Optional[str]= None,
                                     max_tokens: int = 4048,
                                     temperature: float = 0.1,)->BaseModel:
        """Generate structured reponse based on the chat messages history.
        
        Args:
            prompt: Details about structured reponse 
            input: Input for extracting or generating structure
            structure: Pydantic Datamodel for structure
            
        Returns:
            Generated structured response
        """
        try:
            # prepare config for thinking and non thinking
            # Gemini2.5 pro only operates in thinking mode(cant put budget as zero)
            if self.model == "gemini-2.0-flash" or self.model == "gemini-2.5-pro":
                model_config = types.GenerateContentConfig(
                    system_instruction = system_prompt,
                    response_mime_type = "application/json",
                    response_schema = structure,
                    max_output_tokens=max_tokens,
                    temperature= temperature
                    )
            # thinking of flash can be restricted 
            elif self.model == "gemini-2.5-flash":
                model_config = types.GenerateContentConfig(
                    system_instruction = system_prompt,
                    response_mime_type = "application/json",
                    response_schema = structure,
                    max_output_tokens= max_tokens,
                    temperature = temperature,
                    thinking_config=types.ThinkingConfig(thinking_budget=0) # Dont need thinking with flash 2.5 
                    )

            response = self.client.models.generate_content(
                model = self.model,
                config= model_config,
                contents = user_prompt,
                )
            
            input_tok = response.usage_metadata.prompt_token_count
            output_tok = response.usage_metadata.total_token_count - response.usage_metadata.prompt_token_count
    
            # calculate cost of different models 
            cost  = input_tok* (models[self.model]['input_cost']/1000000) + output_tok * (models[self.model]['output_cost']/1000000)
    
            return GeminiStructuredResponse(
                structure = response.parsed,
                input_tokens = input_tok,
                output_tokens = output_tok,
                cost = cost,
                model = self.model,
                success=True,
                )
        except Exception as e:
            logger.error(f"Error generating structured data with Gemini from Google AI studio: {str(e)}")
            return GeminiStructuredResponse(
                structure = None,
                input_tokens = 0,
                output_tokens = 0,
                cost = 0.0,
                model= self.model,
                success=False,
                error_message=f"Error generating structured data with Gemini from Google AI studio: {str(e)}"
                )
