"""
Dialogue Manager for Multi-Turn Conversations.

Tracks conversation context, intent, and entities across multiple turns.
"""

import logging
import re
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class DialogueManager:
    """Manage multi-turn dialogue context and state."""

    def __init__(self):
        """Initialize dialogue manager."""
        self.intent_patterns = {
            "section_query": [r"section\s+\d+", r"BNS\s+\d+", r"BNSS\s+\d+", r"article\s+\d+"],
            "situation_analysis": [r"what if", r"scenario", r"case where", r"happened"],
            "procedure_inquiry": [r"how to", r"procedure", r"process", r"steps"],
            "document_generation": [r"create", r"generate", r"draft", r"prepare document"],
            "case_law": [r"precedent", r"judgment", r"case law", r"supreme court"]
        }

        self.entity_patterns = {
            "section_number": r"(?:section|BNS|BNSS|Article)\s+(\d+[A-Z]?)",
            "person_name": r"(?:Mr\.|Mrs\.|Ms\.)\s+([A-Z][a-z]+)",
            "location": r"(?:in|at)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            "amount": r"Rs\.?\s*(\d+(?:,\d+)*)",
            "date": r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
        }

        logger.info("DialogueManager initialized")

    def detect_intent(self, query: str) -> str:
        """
        Detect user intent from query.

        Args:
            query: User query text

        Returns:
            Detected intent string
        """
        query_lower = query.lower()

        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return intent

        return "general_query"

    def extract_entities(self, query: str) -> Dict[str, List[str]]:
        """
        Extract entities from query.

        Args:
            query: User query text

        Returns:
            Dictionary of entity types to values
        """
        entities = {}

        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, query, re.IGNORECASE)
            if matches:
                entities[entity_type] = matches

        return entities

    def build_context(
        self,
        current_query: str,
        history: List[Dict],
        max_history: int = 5
    ) -> Dict[str, Any]:
        """
        Build conversation context.

        Args:
            current_query: Current user query
            history: List of previous messages
            max_history: Maximum history to include

        Returns:
            Context dictionary
        """
        intent = self.detect_intent(current_query)
        entities = self.extract_entities(current_query)

        # Extract entities from recent history
        historical_entities = {}
        for msg in history[-max_history:]:
            if msg.get("role") == "user":
                hist_entities = self.extract_entities(msg.get("content", ""))
                for k, v in hist_entities.items():
                    if k not in historical_entities:
                        historical_entities[k] = []
                    historical_entities[k].extend(v)

        context = {
            "current_intent": intent,
            "current_entities": entities,
            "historical_entities": historical_entities,
            "turn_count": len(history),
            "last_topic": self._get_last_topic(history),
            "unresolved_entities": self._find_unresolved_entities(entities, historical_entities)
        }

        return context

    def _get_last_topic(self, history: List[Dict]) -> Optional[str]:
        """Extract last discussed topic from history."""
        for msg in reversed(history):
            if msg.get("role") == "assistant" and msg.get("metadata"):
                return msg["metadata"].get("topic")
        return None

    def _find_unresolved_entities(
        self,
        current_entities: Dict,
        historical_entities: Dict
    ) -> List[str]:
        """Find entities mentioned but not fully resolved."""
        unresolved = []

        required_for_document = ["person_name", "location", "date"]

        for entity_type in required_for_document:
            if entity_type not in current_entities and entity_type not in historical_entities:
                unresolved.append(entity_type)

        return unresolved

    def should_clarify(self, context: Dict) -> bool:
        """
        Determine if clarification is needed.

        Args:
            context: Dialogue context

        Returns:
            True if clarification needed
        """
        if context.get("current_intent") == "document_generation":
            if len(context.get("unresolved_entities", [])) > 0:
                return True

        if not context.get("current_entities") and context.get("current_intent") == "section_query":
            return True

        return False

    def generate_clarification(self, context: Dict) -> Optional[str]:
        """
        Generate clarification question.

        Args:
            context: Dialogue context

        Returns:
            Clarification question or None
        """
        unresolved = context.get("unresolved_entities", [])

        if "section_number" in unresolved:
            return "Which section number are you referring to?"

        if "person_name" in unresolved:
            return "Could you provide the person's name?"

        if "location" in unresolved:
            return "In which location did this occur?"

        if "date" in unresolved:
            return "What is the relevant date?"

        return None


# Global instance
_dialogue_manager = None


def get_dialogue_manager() -> DialogueManager:
    """Get or create global dialogue manager instance."""
    global _dialogue_manager
    if _dialogue_manager is None:
        _dialogue_manager = DialogueManager()
    return _dialogue_manager
