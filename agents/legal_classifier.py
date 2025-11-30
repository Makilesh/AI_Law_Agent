# Copyright (c) Microsoft. All rights reserved.

"""
Legal Classification Agent - Analyzes criminal situations and classifies offenses.
"""

import os
from typing import List
from agent_framework import ChatAgent, ChatMessage, Role
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
import logging

from utils.prompts import LAW_CLASSIFICATION_INSTRUCTIONS

load_dotenv()
logger = logging.getLogger(__name__)


class LegalClassificationAgent:
    """Agent specialized in analyzing and classifying criminal situations."""
    
    def __init__(self, chat_client: AzureOpenAIChatClient = None):
        """
        Initialize the Legal Classification Agent.
        
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
            name="LegalClassifier",
            instructions=LAW_CLASSIFICATION_INSTRUCTIONS
        )
        
        logger.info("Legal Classification Agent initialized")
    
    async def classify(
        self, 
        query: str, 
        language: str = "English",
        context: str = "",
        chat_history: List[ChatMessage] = None
    ) -> str:
        """
        Classify a legal query and provide comprehensive analysis.
        
        Args:
            query: User's legal query or situation description
            language: Desired response language
            context: Additional context from vector search
            chat_history: Previous conversation messages
            
        Returns:
            Detailed legal classification and analysis
        """
        try:
            # Build the prompt with context
            prompt = f"""
Analyze the following criminal situation and provide detailed legal insights.

Previous conversation context:
{context if context else "No previous context"}

Current query:
{query}

Provide a comprehensive analysis including:
1. Classification of the offense
2. Applicable sections under Indian Penal Code and other relevant acts
3. Severity level (cognizable/non-cognizable, bailable/non-bailable)
4. Legal procedures that apply
5. Rights of the parties involved
6. Possible defenses or mitigating factors

Respond in {language}.

If this situation is not related to a legal problem or criminal situation, reply with:
"I am an AI-powered legal assistant specialized in Indian criminal law. I provide information and assistance related to criminal offenses, legal sections, and legal procedures under Indian law."
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
            logger.error(f"Error in legal classification: {str(e)}")
            raise


def create_legal_classifier(chat_client: AzureOpenAIChatClient = None) -> ChatAgent:
    """
    Factory function to create a legal classification agent.
    
    Args:
        chat_client: Azure OpenAI chat client
        
    Returns:
        ChatAgent configured for legal classification
    """
    if chat_client is None:
        chat_client = AzureOpenAIChatClient(
            credential=DefaultAzureCredential(),
            azure_endpoint=os.getenv("AZURE_ENDPOINT"),
            api_version=os.getenv("OPENAI_API_VERSION"),
            model_deployment_name=os.getenv("AZURE_CHAT_DEPLOYMENT")
        )
    
    return chat_client.create_agent(
        name="LegalClassifier",
        instructions=LAW_CLASSIFICATION_INSTRUCTIONS
    )
