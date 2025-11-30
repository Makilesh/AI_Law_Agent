# Copyright (c) Microsoft. All rights reserved.

"""
Section Expert Agent - Provides detailed information about legal sections and acts.
"""

import os
from typing import List
from agent_framework import ChatAgent, ChatMessage, Role
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
import logging

from utils.prompts import SECTION_EXPERT_INSTRUCTIONS

load_dotenv()
logger = logging.getLogger(__name__)


class SectionExpertAgent:
    """Agent specialized in providing information about legal sections and acts."""
    
    def __init__(self, chat_client: AzureOpenAIChatClient = None):
        """
        Initialize the Section Expert Agent.
        
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
        
        self.agent = self.chat_client.create_agent(
            name="SectionExpert",
            instructions=SECTION_EXPERT_INSTRUCTIONS
        )
        
        logger.info("Section Expert Agent initialized")
    
    async def explain_section(
        self, 
        query: str, 
        language: str = "English",
        context: str = "",
        chat_history: List[ChatMessage] = None
    ) -> str:
        """
        Explain a legal section or act in detail.
        
        Args:
            query: User's query about a legal section
            language: Desired response language
            context: Additional context from vector search
            chat_history: Previous conversation messages
            
        Returns:
            Detailed explanation of the legal section
        """
        try:
            # Build the prompt with context
            prompt = f"""
Provide detailed information about the legal section or act mentioned in the query.

Context from legal database:
{context if context else "No additional context available"}

Previous conversation:
{self._format_chat_history(chat_history) if chat_history else "No previous conversation"}

Query:
{query}

Provide a comprehensive response including:
1. Section number and act name (IPC/BNS, CrPC/BNSS, etc.)
2. Clear summary of what the section covers
3. Prescribed punishment (if applicable)
4. Key elements that constitute the offense/provision
5. Relevant case laws or precedents
6. Related sections
7. Recent amendments if any

Respond in {language}.

If this is not related to a legal section or act, provide a helpful response directing the user to ask about specific sections.
"""
            
            # Prepare messages
            messages = []
            if chat_history:
                messages.extend(chat_history)
            
            messages.append(ChatMessage(role=Role.USER, text=prompt))
            
            # Get response from agent
            response = await self.agent.run(messages)
            
            # Extract the text from the last message
            if response.messages:
                last_message = response.messages[-1]
                if hasattr(last_message, 'text'):
                    return last_message.text
                elif hasattr(last_message, 'contents'):
                    for content in last_message.contents:
                        if hasattr(content, 'text'):
                            return content.text
            
            return response.text if hasattr(response, 'text') else str(response)
            
        except Exception as e:
            logger.error(f"Error in section explanation: {str(e)}")
            raise
    
    def _format_chat_history(self, chat_history: List[ChatMessage]) -> str:
        """Format chat history for context."""
        if not chat_history:
            return ""
        
        history_text = []
        for msg in chat_history[-6:]:  # Last 6 messages
            role = msg.role.value if hasattr(msg.role, 'value') else str(msg.role)
            text = msg.text if hasattr(msg, 'text') else str(msg)
            history_text.append(f"{role}: {text}")
        
        return "\n".join(history_text)


def create_section_expert(chat_client: AzureOpenAIChatClient = None) -> ChatAgent:
    """
    Factory function to create a section expert agent.
    
    Args:
        chat_client: Azure OpenAI chat client
        
    Returns:
        ChatAgent configured for section expertise
    """
    if chat_client is None:
        chat_client = AzureOpenAIChatClient(
            credential=DefaultAzureCredential(),
            azure_endpoint=os.getenv("AZURE_ENDPOINT"),
            api_version=os.getenv("OPENAI_API_VERSION"),
            model_deployment_name=os.getenv("AZURE_CHAT_DEPLOYMENT")
        )
    
    return chat_client.create_agent(
        name="SectionExpert",
        instructions=SECTION_EXPERT_INSTRUCTIONS
    )
