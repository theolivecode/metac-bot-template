"""
LLM Research Provider

Uses an LLM (like o4-mini-deep-research) to conduct research.
"""
import asyncio
import logging
from typing import Any, Dict, Optional

from .base import ResearchProvider
from ..config import bot_config
from ..utils import BaseLLMClient, LLMClient, LocalLLMClient
from ..prompts import (
    RESEARCH_SYSTEM_PROMPT,
    CLASSIFY_QUESTION_PROMPT,
    SEARCH_ENTITIES_PROMPT,
    ANALYZE_ENTITIES_PROMPT,
    SEARCH_NEWS_PROMPT,
    GENERATE_FINAL_REPORT_PROMPT,
)

logger = logging.getLogger(__name__)


class LLMResearchProvider(ResearchProvider):
    """Research provider using LLM for research."""

    def __init__(
        self,
        llm_client: Optional[BaseLLMClient] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ):
        """
        Initialize the LLM research provider.

        Args:
            llm_client: LLM client instance (can be any BaseLLMClient). If None, creates a new LLMClient.
            model: Model to use for research. If None, uses config default.
            temperature: Temperature for research. If None, uses config default.
        """
        self.llm_client = llm_client or LLMClient()
        self.model = model or bot_config.research_model
        self.temperature = temperature or bot_config.research_temperature

    async def conduct_research(
        self, question: str, question_details: Dict[str, Any] = None
    ) -> str:
        """
        Conduct multi-step research using an LLM.

        This implements a comprehensive research pipeline:
        1. Classify the question into a field
        2. Search for related entities or countries
        3. Analyze personalities, approaches, and relationships
        4. Search for recent news
        5. Generate a final comprehensive report

        Args:
            question: The question to research
            question_details: Optional additional details (resolution criteria, fine print, etc.)

        Returns:
            Research findings from the LLM
        """
        logger.info("=" * 20)
        logger.info("Running Multi-Step Research with LLM...")
        logger.info(f"Model: {self.model}")
        logger.info(f"Research Question: '{question}'")
        logger.info("=" * 20)

        try:
            # Extract field if provided in question_details
            field_context = question_details.get("field", "") if question_details else ""

            # Step 1: Classify the question into a field
            logger.info("\n[Step 1/5] Classifying question into field...")
            field_classification = await self._classify_question(question, field_context)
            logger.info(f"Field Classification:\n{field_classification}")

            # Step 2: Search for related entities or countries
            logger.info("\n[Step 2/5] Searching for related entities and countries...")
            entities = await self._search_entities(question, field_classification)
            logger.info(f"Entities Found:\n{entities}")

            # Step 3: Analyze personalities, approaches, and relationships
            logger.info("\n[Step 3/5] Analyzing entity characteristics and relationships...")
            entity_analysis = await self._analyze_entities(question, entities)
            logger.info(f"Entity Analysis:\n{entity_analysis}")

            # Step 4: Search for recent news
            logger.info("\n[Step 4/5] Searching for recent news...")
            news_summary = await self._search_news(question, field_classification, entities)
            logger.info(f"News Summary:\n{news_summary}")

            # Step 5: Generate final comprehensive report
            logger.info("\n[Step 5/5] Generating final comprehensive report...")
            final_report = await self._generate_final_report(
                question, field_classification, entity_analysis, news_summary
            )

            logger.info("\n======Research Report Start======")
            logger.info(final_report)
            logger.info("\n======Research Report End========")

            return final_report

        except Exception as e:
            logger.error(f"Research failed: {e}")
            return f"Research could not be completed: {str(e)}"

    async def _classify_question(self, question: str, field_context: str = "") -> str:
        """
        Step 1: Classify the question into a field.

        Args:
            question: The question to classify
            field_context: Optional field context provided by the user

        Returns:
            Field classification information
        """
        prompt = CLASSIFY_QUESTION_PROMPT.format(
            question=question,
            field=field_context or "Not provided"
        )

        classification = await self.llm_client.call(
            prompt=prompt,
            model=self.model,
            temperature=self.temperature,
        )

        return classification

    async def _search_entities(self, question: str, field_classification: str) -> str:
        """
        Step 2: Search for related entities or countries.

        Args:
            question: The research question
            field_classification: The field classification from step 1

        Returns:
            List of relevant entities and countries
        """
        prompt = SEARCH_ENTITIES_PROMPT.format(
            question=question,
            field=field_classification
        )

        entities = await self.llm_client.call(
            prompt=prompt,
            model=self.model,
            temperature=self.temperature,
        )

        return entities

    async def _analyze_entities(self, question: str, entities: str) -> str:
        """
        Step 3: Analyze personalities, approaches, and relationships of entities.

        Args:
            question: The research question
            entities: The entities and countries from step 2

        Returns:
            Analysis of entity characteristics and relationships
        """
        prompt = ANALYZE_ENTITIES_PROMPT.format(
            question=question,
            entities=entities
        )

        analysis = await self.llm_client.call(
            prompt=prompt,
            model=self.model,
            temperature=self.temperature,
        )

        return analysis

    async def _search_news(self, question: str, field_classification: str, entities: str) -> str:
        """
        Step 4: Search for 10-20 recent top-ranked news.

        Args:
            question: The research question
            field_classification: The field classification from step 1
            entities: The entities from step 2

        Returns:
            Summary of relevant recent news
        """
        prompt = SEARCH_NEWS_PROMPT.format(
            question=question,
            field=field_classification,
            entities=entities
        )

        news = await self.llm_client.call(
            prompt=prompt,
            model=self.model,
            temperature=self.temperature,
        )

        return news

    async def _generate_final_report(
        self,
        question: str,
        field_classification: str,
        entity_analysis: str,
        news_summary: str
    ) -> str:
        """
        Step 5: Generate final comprehensive report.

        Args:
            question: The research question
            field_classification: The field classification from step 1
            entity_analysis: The entity analysis from step 3
            news_summary: The news summary from step 4

        Returns:
            Final comprehensive research report
        """
        prompt = GENERATE_FINAL_REPORT_PROMPT.format(
            question=question,
            field_classification=field_classification,
            entity_analysis=entity_analysis,
            news_summary=news_summary
        )

        report = await self.llm_client.call(
            prompt=prompt,
            model=self.model,
            temperature=self.temperature,
        )

        return report

    def _build_detailed_query(self, question: str, details: Dict[str, Any]) -> str:
        """
        Build a detailed research query including resolution criteria.

        Args:
            question: The base question
            details: Question details dictionary

        Returns:
            Formatted query string
        """
        query_parts = [RESEARCH_SYSTEM_PROMPT]
        query_parts.append(f"\nThe question is: {question}")

        if resolution_criteria := details.get("resolution_criteria"):
            query_parts.append(
                f"\n\nThis question's outcome will be determined by the specific criteria below:"
            )
            query_parts.append(resolution_criteria)

        if fine_print := details.get("fine_print"):
            query_parts.append(f"\n\nFine Print: {fine_print}")

        return "\n".join(query_parts)
