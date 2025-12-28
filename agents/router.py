# Copyright (c) Microsoft. All rights reserved.

"""
Router Agent - Routes queries to appropriate specialized agents using Gemini.
"""

import os
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
import logging

from utils.gemini_agent import GeminiChatAgent
from agents.legal_classifier import get_classifier_agent
from agents.section_expert import get_section_expert
from dialogue.dialogue_manager import get_dialogue_manager

load_dotenv()
logger = logging.getLogger(__name__)


class RouterAgent:
    """
    Routes incoming queries to the appropriate specialized agent.
    Uses free Gemini API for routing decisions.
    """
    
    def __init__(self):
        """Initialize the router agent."""
        self.agent = GeminiChatAgent(
            name="Router",
            instructions=self._get_system_instruction(),
            model_name="gemini-2.5-flash",
            temperature=0.3
        )
        
        # Get specialized agents
        self.classifier = get_classifier_agent()
        self.section_expert = get_section_expert()
        
        # Get dialogue manager for multi-turn conversations
        self.dialogue_manager = get_dialogue_manager()
        
        logger.info("RouterAgent initialized with Gemini and DialogueManager")
    
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
                response_schema={
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
        context: Optional[Dict[str, Any]] = None,
        history: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Process a query by routing and executing with the appropriate agent.
        Supports multi-turn conversations with dialogue management.
        
        Args:
            query: The user's query
            language: Response language
            context: Optional context dict
            history: Conversation history for multi-turn dialogue
            
        Returns:
            Result from the selected agent with dialogue metadata
        """
        try:
            # Build dialogue context for multi-turn conversations
            dialogue_context = None
            clarification_needed = False
            clarification_question = None
            
            if history:
                dialogue_context = self.dialogue_manager.build_context(query, history)
                clarification_needed = self.dialogue_manager.should_clarify(dialogue_context)
                
                if clarification_needed:
                    clarification_question = self.dialogue_manager.generate_clarification(dialogue_context)
                    logger.info(f"Clarification needed: {clarification_question}")
            
            # Get routing decision
            routing = await self.route(query, context)
            route_name = routing["route"]
            
            # Prepare context
            exec_context = context or {}
            exec_context["language"] = language
            exec_context["dialogue_context"] = dialogue_context
            
            # If clarification is needed, return clarification question
            if clarification_needed and clarification_question:
                return {
                    "response": clarification_question,
                    "query": query,
                    "language": language,
                    "routing": routing,
                    "dialogue_context": dialogue_context,
                    "needs_clarification": True,
                    "clarification_type": "missing_entities"
                }
            
            # Execute with appropriate agent based on routing
            # Most queries should go to SECTION_EXPERT for actual answers
            if route_name == "PDF_PROCESSOR":
                # Only for document-specific queries
                result = await self._handle_general_query(query, language)
                result["routing"] = routing
                result["dialogue_context"] = dialogue_context
                return result
            else:
                # All other queries (CLASSIFIER, SECTION_EXPERT, etc.) → use section expert for answers
                result = await self.section_expert.run(query, exec_context)
                result["routing"] = routing
                result["dialogue_context"] = dialogue_context
                result["needs_clarification"] = False
                return result
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return {
                "error": str(e),
                "response": "I encountered an error processing your request. Please try again.",
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
        
        response = await self.agent.run([
            {"role": "user", "content": prompt}
        ])
        
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
