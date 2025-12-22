"""
Multiple Choice Question Forecaster

Handles forecasting for multiple choice questions.
"""
import asyncio
import datetime
import logging
from typing import Dict, Any, Tuple, List

from ..prompts import MULTIPLE_CHOICE_PROMPT_TEMPLATE
from ..utils import BaseLLMClient, extract_option_probabilities
from ..research import ResearchProvider

logger = logging.getLogger(__name__)


class MultipleChoiceForecaster:
    """Forecaster for multiple choice questions."""

    def __init__(
        self,
        llm_client: BaseLLMClient,
        research_provider: ResearchProvider,
    ):
        """
        Initialize the multiple choice forecaster.

        Args:
            llm_client: LLM client for making predictions (can be any BaseLLMClient)
            research_provider: Research provider for gathering information
        """
        self.llm_client = llm_client
        self.research_provider = research_provider

    async def forecast(
        self, question_details: Dict[str, Any], num_runs: int = 1
    ) -> Tuple[Dict[str, float], str]:
        """
        Generate a multiple choice forecast.

        Args:
            question_details: Dictionary containing question details
            num_runs: Number of forecast runs to aggregate

        Returns:
            Tuple of (probability_yes_per_category, combined_comment)
        """
        logger.info(f"Starting multiple choice forecast with {num_runs} runs")

        # Extract question details
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        title = question_details["title"]
        resolution_criteria = question_details.get("resolution_criteria", "")
        background = question_details.get("description", "")
        fine_print = question_details.get("fine_print", "")
        options = question_details["options"]

        # Conduct research
        summary_report = await self.research_provider.conduct_research(
            question=title,
            question_details=question_details,
        )

        # Build the forecasting prompt
        content = MULTIPLE_CHOICE_PROMPT_TEMPLATE.format(
            title=title,
            today=today,
            background=background,
            resolution_criteria=resolution_criteria,
            fine_print=fine_print,
            summary_report=summary_report,
            options=options,
        )

        # Get multiple forecasts
        probability_yes_per_category_and_comment_pairs = await asyncio.gather(
            *[self._get_single_forecast(content, options) for _ in range(num_runs)]
        )

        # Aggregate results
        probability_yes_per_category_dicts = [
            pair[0] for pair in probability_yes_per_category_and_comment_pairs
        ]
        comments = [pair[1] for pair in probability_yes_per_category_and_comment_pairs]

        # Average probabilities across all runs
        average_probability_yes_per_category = {}
        for option in options:
            probabilities_for_current_option = [
                prob_dict[option] for prob_dict in probability_yes_per_category_dicts
            ]
            average_probability_yes_per_category[option] = sum(
                probabilities_for_current_option
            ) / len(probabilities_for_current_option)

        # Format final comment
        final_comment = self._format_comment(
            average_probability_yes_per_category, comments
        )

        logger.info(f"Multiple choice forecast complete")
        return average_probability_yes_per_category, final_comment

    async def _get_single_forecast(
        self, content: str, options: List[str]
    ) -> Tuple[Dict[str, float], str]:
        """
        Get a single forecast from the LLM.

        Args:
            content: The formatted prompt
            options: List of option labels

        Returns:
            Tuple of (probability_yes_per_category, comment)
        """
        rationale = await self.llm_client.call(content)

        option_probabilities = extract_option_probabilities(rationale, len(options))

        probability_yes_per_category = self._generate_multiple_choice_forecast(
            options, option_probabilities
        )

        comment = (
            f"EXTRACTED_PROBABILITIES: {option_probabilities}\n\n"
            f"GPT's Answer: {rationale}\n\n\n"
        )

        return probability_yes_per_category, comment

    def _generate_multiple_choice_forecast(
        self, options: List[str], option_probabilities: List[float]
    ) -> Dict[str, float]:
        """
        Generate normalized probability distribution for multiple choice options.

        Args:
            options: List of option labels
            option_probabilities: List of raw probability values

        Returns:
            Dictionary mapping options to normalized probabilities

        Raises:
            ValueError: If number of options doesn't match number of probabilities
        """
        if len(options) != len(option_probabilities):
            raise ValueError(
                f"Number of options ({len(options)}) does not match "
                f"number of probabilities ({len(option_probabilities)})"
            )

        # Ensure we are using decimals
        total_sum = sum(option_probabilities)
        decimal_list = [x / total_sum for x in option_probabilities]

        # Normalize (clamp and ensure sum to 1)
        normalized_option_probabilities = self._normalize_list(decimal_list)

        # Create dictionary mapping options to probabilities
        probability_yes_per_category = {
            options[i]: normalized_option_probabilities[i]
            for i in range(len(options))
        }

        return probability_yes_per_category

    def _normalize_list(self, float_list: List[float]) -> List[float]:
        """
        Normalize a list of floats to sum to 1, with clamping.

        Args:
            float_list: List of float values

        Returns:
            Normalized list summing to 1
        """
        # Step 1: Clamp values between 0.01 and 0.99
        clamped_list = [max(min(x, 0.99), 0.01) for x in float_list]

        # Step 2: Calculate the sum of all elements
        total_sum = sum(clamped_list)

        # Step 3: Normalize the list so that all elements add up to 1
        normalized_list = [x / total_sum for x in clamped_list]

        # Step 4: Adjust for any small floating-point errors
        adjustment = 1.0 - sum(normalized_list)
        normalized_list[-1] += adjustment

        return normalized_list

    def _format_comment(
        self, average_probability_yes_per_category: Dict[str, float], comments: list
    ) -> str:
        """
        Format the final comment with all rationales.

        Args:
            average_probability_yes_per_category: Average probabilities
            comments: List of individual comments

        Returns:
            Formatted comment string
        """
        final_comment_sections = [
            f"## Rationale {i+1}\n{comment}" for i, comment in enumerate(comments)
        ]

        final_comment = (
            f"Average Probability Yes Per Category: `{average_probability_yes_per_category}`\n\n"
            + "\n\n".join(final_comment_sections)
        )

        return final_comment
