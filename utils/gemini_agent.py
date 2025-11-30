# Copyright (c) Microsoft. All rights reserved.

"""
Gemini-based Chat Agent - Free alternative to Azure OpenAI.
"""

import os
import google.generativeai as genai
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import logging
import json

load_dotenv()
logger = logging.getLogger(__name__)


class GeminiChatAgent:
    """
    Chat agent using Google Gemini API (free tier).
    Provides similar interface to Azure OpenAI agents.
    """
    
    def __init__(
        self, 
        name: str,
        instructions: str,
        model_name: str = "gemini-1.5-flash",
        temperature: float = 0.7,
        max_tokens: int = 2000
    ):
        """
        Initialize Gemini chat agent.
        
        Args:
            name: Agent name
            instructions: System instructions for the agent
            model_name: Gemini model to use (gemini-1.5-flash is free)
            temperature: Response creativity (0-1)
            max_tokens: Maximum response length
        """
        self.name = name
        self.instructions = instructions
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Configure Gemini API
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        genai.configure(api_key=api_key)
        
        # Initialize model
        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        
        self.model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=generation_config,
            system_instruction=instructions
        )
        
        logger.info(f"Initialized Gemini agent: {name}")
    
    async def run(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Run the agent with conversation messages.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            
        Returns:
            Dict with 'text' and 'messages' keys
        """
        try:
            # Convert messages to Gemini format
            chat_history = []
            user_message = ""
            
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", msg.get("text", ""))
                
                if role == "user":
                    user_message = content
                elif role == "assistant":
                    chat_history.append({
                        "role": "model",
                        "parts": [content]
                    })
            
            # Start chat with history
            chat = self.model.start_chat(history=chat_history)
            
            # Send message
            response = chat.send_message(user_message)
            
            # Extract response text
            response_text = response.text
            
            # Return in Agent Framework-like format
            return {
                "text": response_text,
                "messages": [
                    {
                        "role": "assistant",
                        "text": response_text,
                        "content": response_text
                    }
                ]
            }
            
        except Exception as e:
            logger.error(f"Error in Gemini agent {self.name}: {str(e)}")
            raise
    
    async def generate_structured(
        self, 
        prompt: str, 
        response_schema: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate structured JSON response.
        
        Args:
            prompt: Input prompt
            response_schema: Optional JSON schema for response
            
        Returns:
            Parsed JSON response
        """
        try:
            if response_schema:
                prompt = f"{prompt}\n\nRespond with valid JSON following this schema: {json.dumps(response_schema)}"
            else:
                prompt = f"{prompt}\n\nRespond with valid JSON."
            
            response = self.model.generate_content(prompt)
            response_text = response.text
            
            # Try to extract JSON from response
            try:
                # Remove markdown code blocks if present
                if '```json' in response_text:
                    response_text = response_text.split('```json')[1].split('```')[0].strip()
                elif '```' in response_text:
                    response_text = response_text.split('```')[1].split('```')[0].strip()
                
                return json.loads(response_text)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON response: {response_text[:100]}")
                return {"raw_response": response_text}
                
        except Exception as e:
            logger.error(f"Error generating structured response: {str(e)}")
            raise


def create_gemini_agent(
    name: str,
    instructions: str,
    model_name: str = "gemini-1.5-flash",
    temperature: float = 0.7
) -> GeminiChatAgent:
    """
    Factory function to create a Gemini chat agent.
    
    Args:
        name: Agent name
        instructions: System instructions
        model_name: Gemini model to use
        temperature: Response creativity
        
    Returns:
        GeminiChatAgent instance
    """
    return GeminiChatAgent(
        name=name,
        instructions=instructions,
        model_name=model_name,
        temperature=temperature
    )
