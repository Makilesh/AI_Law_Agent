"""
Multi-Model Manager with Fallback Support
Unified agent interface supporting Gemini, OpenRouter, and Ollama with automatic fallback
Replaces the old gemini_agent.py with enhanced multi-model capabilities
"""

import os
import logging
import httpx
import json
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
logger = logging.getLogger(__name__)


class ModelManager:
    """
    Unified agent interface with multi-model fallback support.
    Manages multiple LLM providers with automatic fallback:
    1. Primary: Google Gemini (configurable version)
    2. Secondary: OpenRouter (when Gemini fails)
    3. Tertiary: Ollama (when both fail)
    
    Compatible with GeminiChatAgent interface for drop-in replacement.
    """
    
    def __init__(
        self,
        name: str = "ModelManager",
        instructions: str = "",
        model_name: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        enable_fallback: bool = True
    ):
        """
        Initialize model manager with fallback support.
        
        Args:
            name: Agent name (for logging)
            instructions: System instructions for all models
            model_name: Gemini model to use (from .env if None)
            temperature: Response creativity (0-1)
            max_tokens: Maximum response length
            enable_fallback: Enable multi-model fallback
        """
        self.name = name
        self.instructions = instructions
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.enable_fallback = enable_fallback
        
        # Load configuration from environment
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        # Use provided model_name or get from env or use default
        if model_name:
            self.gemini_model = model_name
        else:
            self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-preview-0514")
        self.model_name = self.gemini_model  # Alias for compatibility
        
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.openrouter_model = os.getenv("OPENROUTER_MODEL", "openai/gpt-3.5-turbo")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        
        # Initialize Gemini if API key available
        self.gemini_available = False
        if self.gemini_api_key:
            try:
                genai.configure(api_key=self.gemini_api_key)
                self.gemini_client = genai.GenerativeModel(
                    model_name=self.gemini_model,
                    generation_config={
                        "temperature": temperature,
                        "max_output_tokens": max_tokens,
                    },
                    system_instruction=instructions
                )
                self.gemini_available = True
                logger.info(f"✅ Gemini initialized: {self.gemini_model}")
            except Exception as e:
                logger.warning(f"⚠️ Gemini initialization failed: {e}")
        
        # Check OpenRouter availability (only if fallback enabled)
        self.openrouter_available = self.enable_fallback and bool(self.openrouter_api_key)
        if self.openrouter_available:
            logger.info(f"✅ OpenRouter configured: {self.openrouter_model}")
        
        # Check Ollama availability (only if fallback enabled)
        self.ollama_available = self.enable_fallback and self._check_ollama()
        if self.ollama_available:
            logger.info(f"✅ Ollama available: {self.ollama_model}")
        
        # Log agent initialization
        logger.info(f"Initialized agent '{name}' (fallback: {enable_fallback})")
        if enable_fallback:
            available = self.get_available_models()
            if available:
                logger.info(f"   Available models: {', '.join(available)}")
    
    def _check_ollama(self) -> bool:
        """Check if Ollama is running and model is available."""
        try:
            response = httpx.get(
                f"{self.ollama_base_url}/api/tags",
                timeout=2.0
            )
            if response.status_code == 200:
                models = response.json().get("models", [])
                available = any(
                    self.ollama_model in model.get("name", "")
                    for model in models
                )
                return available
        except Exception:
            pass
        return False
    
    async def generate(
        self,
        messages: List[Dict[str, str]],
        force_model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate response with automatic fallback.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            force_model: Force specific model ('gemini', 'openrouter', 'ollama')
            
        Returns:
            Dict with 'text' and 'model_used' keys
        """
        errors = []
        
        # Try models in order (or force specific model)
        models_to_try = []
        if force_model:
            models_to_try = [force_model]
        else:
            if self.gemini_available:
                models_to_try.append('gemini')
            if self.openrouter_available:
                models_to_try.append('openrouter')
            if self.ollama_available:
                models_to_try.append('ollama')
        
        for model_name in models_to_try:
            try:
                if model_name == 'gemini':
                    result = await self._generate_gemini(messages)
                    result['model_used'] = f"gemini ({self.gemini_model})"
                    return result
                elif model_name == 'openrouter':
                    result = await self._generate_openrouter(messages)
                    result['model_used'] = f"openrouter ({self.openrouter_model})"
                    return result
                elif model_name == 'ollama':
                    result = await self._generate_ollama(messages)
                    result['model_used'] = f"ollama ({self.ollama_model})"
                    return result
            except Exception as e:
                error_msg = f"{model_name}: {str(e)}"
                errors.append(error_msg)
                logger.warning(f"❌ {model_name} failed: {e}")
                continue
        
        # All models failed
        raise Exception(
            f"All models failed. Errors: {'; '.join(errors)}"
        )
    
    async def _generate_gemini(
        self,
        messages: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Generate response using Gemini."""
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
        
        # Start chat and send message
        chat = self.gemini_client.start_chat(history=chat_history)
        response = chat.send_message(user_message)
        
        return {
            "text": response.text,
            "messages": [{
                "role": "assistant",
                "text": response.text,
                "content": response.text
            }]
        }
    
    async def _generate_openrouter(
        self,
        messages: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Generate response using OpenRouter."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Format messages for OpenRouter (OpenAI-compatible)
            formatted_messages = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", msg.get("text", ""))
                formatted_messages.append({
                    "role": role,
                    "content": content
                })
            
            # Add system message if not present
            if not any(m["role"] == "system" for m in formatted_messages):
                formatted_messages.insert(0, {
                    "role": "system",
                    "content": self.instructions
                })
            
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openrouter_api_key}",
                    "HTTP-Referer": "http://localhost:8000",
                    "X-Title": "AI Legal Engine"
                },
                json={
                    "model": self.openrouter_model,
                    "messages": formatted_messages,
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens
                }
            )
            response.raise_for_status()
            
            data = response.json()
            response_text = data["choices"][0]["message"]["content"]
            
            return {
                "text": response_text,
                "messages": [{
                    "role": "assistant",
                    "text": response_text,
                    "content": response_text
                }]
            }
    
    async def _generate_ollama(
        self,
        messages: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Generate response using Ollama."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Format messages for Ollama
            formatted_messages = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", msg.get("text", ""))
                formatted_messages.append({
                    "role": role,
                    "content": content
                })
            
            # Add system message
            formatted_messages.insert(0, {
                "role": "system",
                "content": self.instructions
            })
            
            response = await client.post(
                f"{self.ollama_base_url}/api/chat",
                json={
                    "model": self.ollama_model,
                    "messages": formatted_messages,
                    "stream": False,
                    "options": {
                        "temperature": self.temperature,
                        "num_predict": self.max_tokens
                    }
                }
            )
            response.raise_for_status()
            
            data = response.json()
            response_text = data["message"]["content"]
            
            return {
                "text": response_text,
                "messages": [{
                    "role": "assistant",
                    "text": response_text,
                    "content": response_text
                }]
            }
    
    def get_available_models(self) -> List[str]:
        """Get list of available models."""
        available = []
        if self.gemini_available:
            available.append(f"gemini ({self.gemini_model})")
        if self.openrouter_available:
            available.append(f"openrouter ({self.openrouter_model})")
        if self.ollama_available:
            available.append(f"ollama ({self.ollama_model})")
        return available
    
    async def run(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Run the agent with conversation messages (GeminiChatAgent compatibility).
        Uses fallback models if Gemini fails.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            
        Returns:
            Dict with 'text' and 'messages' keys
        """
        try:
            result = await self.generate(messages)
            logger.info(f"✅ {self.name} used: {result.get('model_used', 'unknown')}")
            return result
        except Exception as e:
            logger.error(f"❌ All models failed for {self.name}: {str(e)}")
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
        # Format prompt for JSON output
        if response_schema:
            formatted_prompt = f"{prompt}\n\nRespond with valid JSON following this schema: {json.dumps(response_schema)}"
        else:
            formatted_prompt = f"{prompt}\n\nRespond with valid JSON."
        
        # Create messages format
        messages = [{"role": "user", "content": formatted_prompt}]
        
        try:
            # Try to use Gemini directly for structured output (it's better at it)
            if self.gemini_available:
                response = self.gemini_client.generate_content(formatted_prompt)
                response_text = response.text
            else:
                # Fall back to generate method
                result = await self.generate(messages)
                response_text = result.get("text", "")
            
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


# ============================================================
# Factory Functions (for backward compatibility)
# ============================================================

def create_model_manager(
    name: str = "ModelManager",
    instructions: str = "",
    model_name: str = None,
    temperature: float = 0.7,
    max_tokens: int = 2000
) -> ModelManager:
    """
    Factory function to create a model manager with fallback support.
    
    Args:
        name: Agent name
        instructions: System instructions
        model_name: Model to use (Gemini model name)
        temperature: Response creativity
        max_tokens: Maximum response length
        
    Returns:
        ModelManager instance
    """
    return ModelManager(
        name=name,
        instructions=instructions,
        model_name=model_name,
        temperature=temperature,
        max_tokens=max_tokens
    )


def create_gemini_agent(
    name: str,
    instructions: str,
    model_name: str = None,
    temperature: float = 0.7
) -> ModelManager:
    """
    Factory function to create an agent (backward compatibility with GeminiChatAgent).
    
    Args:
        name: Agent name
        instructions: System instructions
        model_name: Gemini model to use
        temperature: Response creativity
        
    Returns:
        ModelManager instance
    """
    return ModelManager(
        name=name,
        instructions=instructions,
        model_name=model_name,
        temperature=temperature
    )


# Alias for compatibility
GeminiChatAgent = ModelManager
