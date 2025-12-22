"""
Base Research Provider

Abstract base class for research providers.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class ResearchProvider(ABC):
    """Abstract base class for research providers."""

    @abstractmethod
    async def conduct_research(self, question: str, question_details: Dict[str, Any] = None) -> str:
        """
        Conduct research on a question.

        Args:
            question: The question to research
            question_details: Optional additional details about the question

        Returns:
            Research findings as a string
        """
        pass
