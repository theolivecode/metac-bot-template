"""
Binary Question Forecaster

Handles forecasting for binary (yes/no) questions.
"""
import asyncio
import datetime
import logging
from typing import Dict, Any, Tuple

import numpy as np

from ..prompts import BINARY_PROMPT_TEMPLATE
from ..utils import BaseLLMClient, extract_probability_percentage
from ..research import ResearchProvider

logger = logging.getLogger(__name__)


class BinaryForecaster:
    """Forecaster for binary questions."""

    def __init__(
        self,
        llm_client: BaseLLMClient,
        research_provider: ResearchProvider,
    ):
        """
        Initialize the binary forecaster.

        Args:
            llm_client: LLM client for making predictions (can be any BaseLLMClient)
            research_provider: Research provider for gathering information
        """
        self.llm_client = llm_client
        self.research_provider = research_provider

    async def forecast(
        self, question_details: Dict[str, Any], num_runs: int = 1
    ) -> Tuple[float, str]:
        """
        Generate a binary forecast.

        Args:
            question_details: Dictionary containing question details
            num_runs: Number of forecast runs to aggregate

        Returns:
            Tuple of (median_probability, combined_comment)
        """
        logger.info(f"Starting binary forecast with {num_runs} runs")

        # Extract question details
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        title = question_details["title"]
        resolution_criteria = question_details.get("resolution_criteria", "")
        background = question_details.get("description", "")
        fine_print = question_details.get("fine_print", "")

        # Conduct research
        summary_report = await self.research_provider.conduct_research(
            question=title,
            question_details=question_details,
        )

        # Build the forecasting prompt
        content = BINARY_PROMPT_TEMPLATE.format(
            title=title,
            today=today,
            background=background,
            resolution_criteria=resolution_criteria,
            fine_print=fine_print,
            summary_report=summary_report,
        )

        # Get multiple forecasts
        probability_and_comment_pairs = await asyncio.gather(
            *[self._get_single_forecast(content) for _ in range(num_runs)]
        )

        # Aggregate results
        probabilities = [pair[0] for pair in probability_and_comment_pairs]
        comments = [pair[1] for pair in probability_and_comment_pairs]

        median_probability = float(np.median(probabilities))

        # Format final comment
        final_comment = self._format_comment(median_probability, comments)

        logger.info(f"Binary forecast complete: {median_probability:.2%}")
        return median_probability, final_comment

    async def _get_single_forecast(self, content: str) -> Tuple[float, str]:
        """
        Get a single forecast from the LLM.

        Args:
            content: The formatted prompt

        Returns:
            Tuple of (probability, comment)
        """
        rationale = await self.llm_client.call(content)

        probability = extract_probability_percentage(rationale)

        comment = (
            f"Extracted Probability: {probability:.2%}\n\n"
            f"GPT's Answer: {rationale}\n\n\n"
        )

        return probability, comment

    def _format_comment(self, median_probability: float, comments: list) -> str:
        """
        Format the final comment with all rationales.

        Args:
            median_probability: The median probability across all runs
            comments: List of individual comments

        Returns:
            Formatted comment string
        """
        final_comment_sections = [
            f"## Rationale {i+1}\n{comment}" for i, comment in enumerate(comments)
        ]

        final_comment = (
            f"Median Probability: {median_probability:.2%}\n\n"
            + "\n\n".join(final_comment_sections)
        )

        return final_comment
