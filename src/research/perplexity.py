"""
Perplexity Research Provider

Uses Perplexity API for online research.
"""
import logging
from typing import Any, Dict, Optional

import requests

from .base import ResearchProvider
from ..config import api_config
from ..prompts import RESEARCH_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class PerplexityResearchProvider(ResearchProvider):
    """Research provider using Perplexity API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "sonar-reasoning-pro",
    ):
        """
        Initialize the Perplexity research provider.

        Args:
            api_key: Perplexity API key. If None, uses config.
            model: Perplexity model to use.
        """
        self.api_key = api_key or api_config.perplexity_api_key
        self.model = model
        self.base_url = "https://api.perplexity.ai/chat/completions"

    async def conduct_research(
        self, question: str, question_details: Dict[str, Any] = None
    ) -> str:
        """
        Conduct research using Perplexity API.

        Args:
            question: The question to research
            question_details: Optional additional details

        Returns:
            Research findings from Perplexity
        """
        logger.info(f"Using Perplexity for research question: {question}")
        logger.info("Running research...")

        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {self.api_key}",
            "content-type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": RESEARCH_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": question,
                },
            ],
        }

        try:
            response = requests.post(
                url=self.base_url,
                json=payload,
                headers=headers,
            )

            if not response.ok:
                logger.error(f"Perplexity API error: {response.text}")
                raise RuntimeError(f"Perplexity API error: {response.text}")

            content = response.json()["choices"][0]["message"]["content"]

            logger.info("\n======Research Start======")
            logger.info(content)
            logger.info("\n======Research End========")

            return content

        except Exception as e:
            logger.error(f"Perplexity research failed: {e}")
            return f"Research could not be completed: {str(e)}"
