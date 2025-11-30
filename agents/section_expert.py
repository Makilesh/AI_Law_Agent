# Copyright (c) Microsoft. All rights reserved.

"""
Section Expert Agent - Provides detailed information about specific legal sections using Gemini.
"""

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import logging

from utils.gemini_agent import GeminiChatAgent
from utils.vector_store import search_legal_context

load_dotenv()
logger = logging.getLogger(__name__)


class SectionExpertAgent:
    """
    Provides detailed explanations of legal sections.
    Uses free Gemini API with vector search context.
    """
    
    def __init__(self):
        """Initialize the section expert agent."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        self.agent = GeminiChatAgent(
            api_key=api_key,
            model_name="gemini-1.5-flash",
            system_instruction=self._get_system_instruction()
        )
        
        logger.info("SectionExpertAgent initialized with Gemini")
    
    def _get_system_instruction(self) -> str:
        """Get the system instruction for section expertise."""
        return """You are a legal expert specializing in Indian criminal law sections.

Your role is to provide detailed, accurate explanations of legal sections including:
- The exact text and wording of the section
- What the section covers and prohibits
- Penalties and punishments prescribed
- Key elements required to prove the offense
- Important case law and precedents
- Practical applications and examples
- Related sections and cross-references

When explaining sections:
1. Start with the section number and title
2. Quote the relevant legal text
3. Explain in simple terms what it means
4. Discuss penalties and consequences
5. Provide real-world examples
6. Mention related sections

Always cite sources and be accurate. If you're unsure about specific details, say so.
Focus on Indian Penal Code (IPC), Criminal Procedure Code (CrPC), and other Indian criminal laws."""
    
    async def explain_section(
        self,
        section_query: str,
        language: str = "English",
        context: str = ""
    ) -> str:
        """
        Explain a specific legal section in detail.
        
        Args:
            section_query: Query about a specific section (e.g., "IPC 420", "Section 498A")
            language: Language for the response
            context: Additional context from vector search
            
        Returns:
            Detailed explanation of the section
        """
        try:
            # Search for relevant legal context
            if not context:
                context = await search_legal_context(section_query, n_results=3)
            
            # Build prompt with context
            prompt = f"""
Provide a comprehensive explanation of the following legal section.

Section Query: {section_query}

Relevant Legal Context:
{context if context else "No additional context available"}

Please provide:
1. Section number and official title
2. Full text of the section
3. Simple explanation of what it means
4. Penalties and punishments
5. Key elements to prove the offense
6. Practical examples
7. Related sections

Respond in {language}.
"""
            
            # Get response
            response = await self.agent.run(prompt)
            return response["text"]
            
        except Exception as e:
            logger.error(f"Error explaining section: {str(e)}")
            return f"I apologize, but I encountered an error while processing your request about {section_query}. Please try again."
    
    async def run(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run the section expert agent (compatible with workflow executor).
        
        Args:
            query: The user's query about a legal section
            context: Optional context dict
            
        Returns:
            Result dict with section explanation
        """
        language = context.get("language", "English") if context else "English"
        vector_context = context.get("vector_context", "") if context else ""
        
        explanation = await self.explain_section(query, language, vector_context)
        
        return {
            "section_query": query,
            "explanation": explanation,
            "language": language
        }


# Create global instance
_section_expert = None


def get_section_expert() -> SectionExpertAgent:
    """Get or create the global section expert instance."""
    global _section_expert
    if _section_expert is None:
        _section_expert = SectionExpertAgent()
    return _section_expert
