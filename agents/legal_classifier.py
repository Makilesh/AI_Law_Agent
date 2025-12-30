# Copyright (c) Microsoft. All rights reserved.

"""
Legal Query Classifier Agent - Routes queries to appropriate handlers using Gemini.
"""

import os
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import logging

from utils.gemini_agent import GeminiChatAgent
from models.schemas import ClassifierResult

load_dotenv()
logger = logging.getLogger(__name__)


class LegalClassifierAgent:
    """
    Classifies legal queries to determine routing.
    Uses free Gemini API.
    """
    
    def __init__(self):
        """Initialize the classifier agent."""
        self.agent = GeminiChatAgent(
            name="LegalClassifier",
            instructions=self._get_system_instruction(),
            model_name="gemini-2.0-flash",
            temperature=0.3
        )
        
        logger.info("LegalClassifierAgent initialized with Gemini")
    
    def _get_system_instruction(self) -> str:
        """Get the system instruction for classification."""
        return """You are a legal query classifier for Indian criminal law.

Your job is to analyze user queries and classify them into categories:

1. LAW_QUERY: Questions about specific laws (IPC, CrPC, evidence acts, etc.)
   - Examples: "What is IPC 302?", "Explain sedition law", "What are the provisions of CrPC 41?"

2. SECTION_QUERY: Questions about specific sections of laws
   - Examples: "Section 420 IPC", "What is Section 498A?", "Details of Section 377"

3. LEGAL_ADVICE: Questions seeking legal advice or case-specific guidance
   - Examples: "What should I do if I'm accused?", "Can I file an FIR?", "Am I eligible for bail?"

4. DOCUMENT_QUERY: Questions about legal documents, forms, or procedures
   - Examples: "How to file a petition?", "What documents are needed for bail?", "Format of affidavit"

5. GENERAL: General legal questions not fitting above categories
   - Examples: "What is the legal system in India?", "Types of courts", "Legal rights"

You must respond with ONLY a JSON object in this format:
{
    "category": "one of the categories above",
    "confidence": 0.95,
    "reasoning": "brief explanation",
    "extracted_info": {
        "section_number": "420" (if applicable),
        "law_name": "IPC" (if applicable),
        "query_intent": "brief summary"
    }
}

Be precise and accurate. Use extracted_info to capture key details from the query."""
    
    async def classify(self, query: str) -> ClassifierResult:
        """
        Classify a legal query.
        
        Args:
            query: The user's legal query
            
        Returns:
            ClassifierResult with category and metadata
        """
        try:
            # Use structured generation for reliable JSON
            response = await self.agent.generate_structured(
                prompt=f"Classify this legal query:\n\nQuery: {query}",
                response_schema={
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "enum": ["LAW_QUERY", "SECTION_QUERY", "LEGAL_ADVICE", "DOCUMENT_QUERY", "GENERAL"]
                        },
                        "confidence": {"type": "number"},
                        "reasoning": {"type": "string"},
                        "extracted_info": {
                            "type": "object",
                            "properties": {
                                "section_number": {"type": "string"},
                                "law_name": {"type": "string"},
                                "query_intent": {"type": "string"}
                            }
                        }
                    },
                    "required": ["category", "confidence", "reasoning"]
                }
            )
            
            # Create ClassifierResult
            result = ClassifierResult(
                category=response.get("category", "GENERAL"),
                confidence=response.get("confidence", 0.8),
                reasoning=response.get("reasoning", ""),
                extracted_info=response.get("extracted_info", {})
            )
            
            logger.info(f"Classified query as: {result.category} (confidence: {result.confidence})")
            return result
            
        except Exception as e:
            logger.error(f"Classification error: {str(e)}")
            # Fallback classification
            return ClassifierResult(
                category="GENERAL",
                confidence=0.5,
                reasoning=f"Error during classification: {str(e)}",
                extracted_info={}
            )
    
    async def run(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run the classifier agent (compatible with workflow executor).
        
        Args:
            query: The user's query
            context: Optional context dict
            
        Returns:
            Result dict with classification
        """
        result = await self.classify(query)
        
        return {
            "category": result.category,
            "confidence": result.confidence,
            "reasoning": result.reasoning,
            "extracted_info": result.extracted_info,
            "original_query": query
        }


# Create global instance
_classifier_agent = None


def get_classifier_agent() -> LegalClassifierAgent:
    """Get or create the global classifier agent instance."""
    global _classifier_agent
    if _classifier_agent is None:
        _classifier_agent = LegalClassifierAgent()
    return _classifier_agent
