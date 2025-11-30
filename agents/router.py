# Copyright (c) Microsoft. All rights reserved.

"""
Router Agent - Routes queries to appropriate specialized agents using Gemini.
"""

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import logging

from utils.gemini_agent import GeminiChatAgent
from agents.legal_classifier import get_classifier_agent
from agents.section_expert import get_section_expert

load_dotenv()
logger = logging.getLogger(__name__)


class RouterAgent:
    """
    Routes incoming queries to the appropriate specialized agent.
    Uses free Gemini API for routing decisions.
    """
    
    def __init__(self):
        """Initialize the router agent."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        self.agent = GeminiChatAgent(
            api_key=api_key,
            model_name="gemini-1.5-flash",
            system_instruction=self._get_system_instruction()
        )
        
        # Get specialized agents
        self.classifier = get_classifier_agent()
        self.section_expert = get_section_expert()
        
        logger.info("RouterAgent initialized with Gemini")
    
    def _get_system_instruction(self) -> str:
        """Get the system instruction for routing."""
        return """You are a routing agent for a legal assistant system.

Your job is to analyze user queries and decide which specialized agent should handle them:

1. CLASSIFIER: For general legal questions, situation analysis, crime classification
2. SECTION_EXPERT: For questions about specific legal sections (IPC, CrPC, etc.)
3. PDF_PROCESSOR: For questions about uploaded documents
4. GENERAL_ASSISTANT: For general questions and conversation

Respond with ONLY a JSON object:
{
    "route": "CLASSIFIER|SECTION_EXPERT|PDF_PROCESSOR|GENERAL_ASSISTANT",
    "confidence": 0.95,
    "reasoning": "why this route"
}

Be decisive and accurate."""
    
    async def route(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Route a query to the appropriate agent.
        
        Args:
            query: The user's query
            context: Optional context dict
            
        Returns:
            Routing decision with agent name and metadata
        """
        try:
            # Get routing decision
            response = await self.agent.generate_structured(
                prompt=f"Route this query to the appropriate agent:\n\nQuery: {query}",
                schema={
                    "type": "object",
                    "properties": {
                        "route": {
                            "type": "string",
                            "enum": ["CLASSIFIER", "SECTION_EXPERT", "PDF_PROCESSOR", "GENERAL_ASSISTANT"]
                        },
                        "confidence": {"type": "number"},
                        "reasoning": {"type": "string"}
                    },
                    "required": ["route", "confidence", "reasoning"]
                }
            )
            
            route_name = response.get("route", "GENERAL_ASSISTANT")
            
            logger.info(f"Routed query to: {route_name} (confidence: {response.get('confidence', 0.8)})")
            
            return {
                "route": route_name,
                "confidence": response.get("confidence", 0.8),
                "reasoning": response.get("reasoning", ""),
                "original_query": query
            }
            
        except Exception as e:
            logger.error(f"Routing error: {str(e)}")
            return {
                "route": "GENERAL_ASSISTANT",
                "confidence": 0.5,
                "reasoning": f"Error during routing: {str(e)}",
                "original_query": query
            }
    
    async def process_query(
        self,
        query: str,
        language: str = "English",
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a query by routing and executing with the appropriate agent.
        
        Args:
            query: The user's query
            language: Response language
            context: Optional context dict
            
        Returns:
            Result from the selected agent
        """
        try:
            # Get routing decision
            routing = await self.route(query, context)
            route_name = routing["route"]
            
            # Prepare context
            exec_context = context or {}
            exec_context["language"] = language
            
            # Execute with appropriate agent
            if route_name == "SECTION_EXPERT":
                result = await self.section_expert.run(query, exec_context)
            elif route_name == "CLASSIFIER":
                result = await self.classifier.run(query, exec_context)
            else:
                # Use general assistant
                result = await self._handle_general_query(query, language)
            
            # Add routing metadata
            result["routing"] = routing
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return {
                "error": str(e),
                "message": "I encountered an error processing your request. Please try again.",
                "original_query": query
            }
    
    async def _handle_general_query(self, query: str, language: str) -> Dict[str, Any]:
        """Handle general queries that don't need specialized agents."""
        prompt = f"""
The user asked: {query}

Provide a helpful response. If this is a greeting or general question, respond appropriately.
If this is a legal question, explain that you can help with:
- Questions about Indian criminal law sections
- Legal situation analysis
- Information about IPC, CrPC, and other Indian criminal laws

Respond in {language}.
"""
        
        response = await self.agent.run(prompt)
        
        return {
            "response": response["text"],
            "query": query,
            "language": language
        }


# Create global instance
_router_agent = None


def get_router_agent() -> RouterAgent:
    """Get or create the global router agent instance."""
    global _router_agent
    if _router_agent is None:
        _router_agent = RouterAgent()
    return _router_agent
