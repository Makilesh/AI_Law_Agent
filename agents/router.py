# Copyright (c) Microsoft. All rights reserved.

"""
Router Agent - Intelligently routes queries to appropriate specialist agents.
"""

import os
from typing import Any
from agent_framework import ChatAgent, ChatMessage, Role
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
import logging
import json

from utils.prompts import ROUTER_INSTRUCTIONS
from models.schemas import QueryDecision

load_dotenv()
logger = logging.getLogger(__name__)


class RouterAgent:
    """Agent that determines which specialist agent should handle a query."""
    
    def __init__(self, chat_client: AzureOpenAIChatClient = None):
        """
        Initialize the Router Agent.
        
        Args:
            chat_client: Azure OpenAI chat client. If None, creates a new one.
        """
        if chat_client is None:
            self.chat_client = AzureOpenAIChatClient(
                credential=DefaultAzureCredential(),
                azure_endpoint=os.getenv("AZURE_ENDPOINT"),
                api_version=os.getenv("OPENAI_API_VERSION"),
                model_deployment_name=os.getenv("AZURE_CHAT_DEPLOYMENT")
            )
        else:
            self.chat_client = chat_client
        
        # Create agent with structured output
        self.agent = self.chat_client.create_agent(
            name="QueryRouter",
            instructions=ROUTER_INSTRUCTIONS,
        )
        
        logger.info("Router Agent initialized")
    
    async def route_query(self, query: str) -> QueryDecision:
        """
        Analyze query and determine which agent should handle it.
        
        Args:
            query: User's legal query
            
        Returns:
            QueryDecision with routing information
        """
        try:
            prompt = f"""
Analyze this legal query and determine if it should be routed to:
1. 'law' agent - for criminal situation analysis and offense classification
2. 'section' agent - for information about specific legal sections

Query: {query}

Respond with:
- query_type: either "law" or "section"
- confidence: score between 0 and 1
- reasoning: brief explanation

Format your response as JSON.
"""
            
            messages = [ChatMessage(role=Role.USER, text=prompt)]
            response = await self.agent.run(messages)
            
            # Extract response text
            response_text = ""
            if response.messages:
                last_message = response.messages[-1]
                if hasattr(last_message, 'text'):
                    response_text = last_message.text
                elif hasattr(last_message, 'contents'):
                    for content in last_message.contents:
                        if hasattr(content, 'text'):
                            response_text = content.text
                            break
            
            # Parse JSON response
            try:
                # Try to extract JSON from the response
                response_text = response_text.strip()
                if '```json' in response_text:
                    response_text = response_text.split('```json')[1].split('```')[0].strip()
                elif '```' in response_text:
                    response_text = response_text.split('```')[1].split('```')[0].strip()
                
                decision_data = json.loads(response_text)
                return QueryDecision(**decision_data)
            except Exception as parse_error:
                logger.warning(f"Failed to parse router response as JSON: {parse_error}")
                # Fallback: analyze query with simple heuristics
                return self._fallback_routing(query)
                
        except Exception as e:
            logger.error(f"Error in query routing: {str(e)}")
            # Fallback to default routing
            return self._fallback_routing(query)
    
    def _fallback_routing(self, query: str) -> QueryDecision:
        """
        Simple heuristic-based routing as fallback.
        
        Args:
            query: User's query
            
        Returns:
            QueryDecision based on simple heuristics
        """
        query_lower = query.lower()
        
        # Keywords that indicate section query
        section_keywords = [
            'section', 'sec', 'ipc', 'crpc', 'act', 'article',
            'what is', 'explain', 'define', 'definition', 
            'punishment for', 'penalty', 'bns', 'bnss'
        ]
        
        # Check for section patterns (e.g., "302", "420 IPC")
        import re
        if re.search(r'\b\d{1,4}\b.*(?:ipc|crpc|bns|act)', query_lower):
            return QueryDecision(
                query_type="section",
                confidence=0.8,
                reasoning="Query contains section number pattern"
            )
        
        # Check for section keywords
        if any(keyword in query_lower for keyword in section_keywords):
            return QueryDecision(
                query_type="section",
                confidence=0.7,
                reasoning="Query contains section-related keywords"
            )
        
        # Default to law classification for situation analysis
        return QueryDecision(
            query_type="law",
            confidence=0.6,
            reasoning="Query appears to describe a legal situation for classification"
        )


def is_classification_query(decision: Any) -> bool:
    """
    Condition function to check if query should go to classification agent.
    
    Args:
        decision: QueryDecision object
        
    Returns:
        True if query should be routed to legal classifier
    """
    if isinstance(decision, QueryDecision):
        return decision.query_type == "law"
    return False


def is_section_query(decision: Any) -> bool:
    """
    Condition function to check if query should go to section expert.
    
    Args:
        decision: QueryDecision object
        
    Returns:
        True if query should be routed to section expert
    """
    if isinstance(decision, QueryDecision):
        return decision.query_type == "section"
    return False
