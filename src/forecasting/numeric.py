"""
Numeric Question Forecaster

Handles forecasting for numeric and discrete questions.
"""
import asyncio
import datetime
import logging
from typing import Dict, Any, Tuple, List, Optional

import numpy as np

from ..prompts import NUMERIC_PROMPT_TEMPLATE
from ..utils import BaseLLMClient, extract_percentiles
from ..research import ResearchProvider
from ..config import QuestionType

logger = logging.getLogger(__name__)


class NumericForecaster:
    """Forecaster for numeric and discrete questions."""

    def __init__(
        self,
        llm_client: BaseLLMClient,
        research_provider: ResearchProvider,
    ):
        """
        Initialize the numeric forecaster.

        Args:
            llm_client: LLM client for making predictions (can be any BaseLLMClient)
            research_provider: Research provider for gathering information
        """
        self.llm_client = llm_client
        self.research_provider = research_provider

    async def forecast(
        self, question_details: Dict[str, Any], num_runs: int = 1
    ) -> Tuple[List[float], str]:
        """
        Generate a numeric forecast.

        Args:
            question_details: Dictionary containing question details
            num_runs: Number of forecast runs to aggregate

        Returns:
            Tuple of (median_cdf, combined_comment)
        """
        logger.info(f"Starting numeric forecast with {num_runs} runs")

        # Extract question details
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        title = question_details["title"]
        resolution_criteria = question_details.get("resolution_criteria", "")
        background = question_details.get("description", "")
        fine_print = question_details.get("fine_print", "")
        question_type = question_details["type"]
        scaling = question_details["scaling"]
        open_upper_bound = question_details.get("open_upper_bound", False)
        open_lower_bound = question_details.get("open_lower_bound", False)
        unit_of_measure = question_details.get("unit") or "Not stated (please infer this)"
        upper_bound = scaling["range_max"]
        lower_bound = scaling["range_min"]
        zero_point = scaling.get("zero_point")

        # Determine CDF size
        if question_type == QuestionType.DISCRETE:
            outcome_count = scaling["inbound_outcome_count"]
            cdf_size = outcome_count + 1
        else:
            cdf_size = 201

        # Create bound messages
        upper_bound_message = (
            "" if open_upper_bound else f"The outcome can not be higher than {upper_bound}."
        )
        lower_bound_message = (
            "" if open_lower_bound else f"The outcome can not be lower than {lower_bound}."
        )

        # Conduct research
        summary_report = await self.research_provider.conduct_research(
            question=title,
            question_details=question_details,
        )

        # Build the forecasting prompt
        content = NUMERIC_PROMPT_TEMPLATE.format(
            title=title,
            today=today,
            background=background,
            resolution_criteria=resolution_criteria,
            fine_print=fine_print,
            summary_report=summary_report,
            lower_bound_message=lower_bound_message,
            upper_bound_message=upper_bound_message,
            units=unit_of_measure,
        )

        # Get multiple forecasts
        cdf_and_comment_pairs = await asyncio.gather(
            *[
                self._get_single_forecast(
                    content,
                    question_type,
                    open_upper_bound,
                    open_lower_bound,
                    upper_bound,
                    lower_bound,
                    zero_point,
                    cdf_size,
                )
                for _ in range(num_runs)
            ]
        )

        # Aggregate results
        cdfs = [pair[0] for pair in cdf_and_comment_pairs]
        comments = [pair[1] for pair in cdf_and_comment_pairs]

        all_cdfs = np.array(cdfs)
        median_cdf = np.median(all_cdfs, axis=0).tolist()

        # Format final comment
        final_comment = self._format_comment(median_cdf, comments)

        logger.info(f"Numeric forecast complete (CDF size: {len(median_cdf)})")
        return median_cdf, final_comment

    async def _get_single_forecast(
        self,
        content: str,
        question_type: str,
        open_upper_bound: bool,
        open_lower_bound: bool,
        upper_bound: float,
        lower_bound: float,
        zero_point: Optional[float],
        cdf_size: int,
    ) -> Tuple[List[float], str]:
        """
        Get a single numeric forecast from the LLM.

        Args:
            content: The formatted prompt
            question_type: Type of question
            open_upper_bound: Whether upper bound is open
            open_lower_bound: Whether lower bound is open
            upper_bound: Upper bound value
            lower_bound: Lower bound value
            zero_point: Zero point for log scaling
            cdf_size: Size of the CDF array

        Returns:
            Tuple of (cdf, comment)
        """
        rationale = await self.llm_client.call(content)

        percentile_values = extract_percentiles(rationale)

        cdf = self._generate_continuous_cdf(
            percentile_values,
            question_type,
            open_upper_bound,
            open_lower_bound,
            upper_bound,
            lower_bound,
            zero_point,
            cdf_size,
        )

        comment = (
            f"Extracted Percentile values: {percentile_values}\n\n"
            f"GPT's Answer: {rationale}\n\n\n"
        )

        return cdf, comment

    def _generate_continuous_cdf(
        self,
        percentile_values: Dict[int, float],
        question_type: str,
        open_upper_bound: bool,
        open_lower_bound: bool,
        upper_bound: float,
        lower_bound: float,
        zero_point: Optional[float],
        cdf_size: int,
    ) -> List[float]:
        """
        Generate a continuous CDF from percentile values.

        Args:
            percentile_values: Dictionary mapping percentiles to values
            question_type: Type of question
            open_upper_bound: Whether upper bound is open
            open_lower_bound: Whether lower bound is open
            upper_bound: Upper bound value
            lower_bound: Lower bound value
            zero_point: Zero point for log scaling
            cdf_size: Size of the output CDF

        Returns:
            List of CDF values
        """
        percentile_max = max(float(key) for key in percentile_values.keys())
        percentile_min = min(float(key) for key in percentile_values.keys())
        range_min = lower_bound
        range_max = upper_bound
        range_size = range_max - range_min
        buffer = 1 if range_size > 100 else 0.01 * range_size

        # Adjust values at the bounds
        for percentile, value in list(percentile_values.items()):
            if not open_lower_bound and value <= range_min + buffer:
                percentile_values[percentile] = range_min + buffer
            if not open_upper_bound and value >= range_max - buffer:
                percentile_values[percentile] = range_max - buffer

        # Set CDF values outside range
        if open_upper_bound:
            if range_max > percentile_values[percentile_max]:
                percentile_values[int(100 - (0.5 * (100 - percentile_max)))] = range_max
        else:
            percentile_values[100] = range_max

        if open_lower_bound:
            if range_min < percentile_values[percentile_min]:
                percentile_values[int(0.5 * percentile_min)] = range_min
        else:
            percentile_values[0] = range_min

        sorted_percentile_values = dict(sorted(percentile_values.items()))

        # Normalize percentile keys to 0-1 range
        normalized_percentile_values = {
            float(key) / 100: value for key, value in sorted_percentile_values.items()
        }

        # Create value -> percentile mapping
        value_percentiles = {
            value: key for key, value in normalized_percentile_values.items()
        }

        # Generate CDF x-axis locations (with optional log scaling)
        cdf_xaxis = self._generate_cdf_locations(range_min, range_max, zero_point, cdf_size)

        # Interpolate to get CDF values
        continuous_cdf = self._linear_interpolation(cdf_xaxis, value_percentiles)

        return continuous_cdf

    def _generate_cdf_locations(
        self,
        range_min: float,
        range_max: float,
        zero_point: Optional[float],
        cdf_size: int,
    ) -> List[float]:
        """
        Generate x-axis locations for the CDF.

        Args:
            range_min: Minimum value
            range_max: Maximum value
            zero_point: Zero point for log scaling (None for linear)
            cdf_size: Number of points

        Returns:
            List of x-axis locations
        """
        if zero_point is None:
            # Linear scaling
            scale = lambda x: range_min + (range_max - range_min) * x
        else:
            # Log scaling
            deriv_ratio = (range_max - zero_point) / (range_min - zero_point)
            scale = lambda x: range_min + (range_max - range_min) * (
                deriv_ratio**x - 1
            ) / (deriv_ratio - 1)

        return [scale(x) for x in np.linspace(0, 1, cdf_size)]

    def _linear_interpolation(
        self, x_values: List[float], xy_pairs: Dict[float, float]
    ) -> List[float]:
        """
        Perform linear interpolation.

        Args:
            x_values: X values to interpolate at
            xy_pairs: Known (x, y) pairs as a dictionary

        Returns:
            Interpolated y values
        """
        # Sort the xy_pairs by x-values
        sorted_pairs = sorted(xy_pairs.items())

        # Extract sorted x and y values
        known_x = [pair[0] for pair in sorted_pairs]
        known_y = [pair[1] for pair in sorted_pairs]

        y_values = []

        for x in x_values:
            # Check if x is exactly in the known x values
            if x in known_x:
                y_values.append(known_y[known_x.index(x)])
            else:
                # Find the indices of the two nearest known x-values
                i = 0
                while i < len(known_x) and known_x[i] < x:
                    i += 1

                # If x is outside the range, use the nearest endpoint
                if i == 0:
                    y_values.append(known_y[0])
                elif i == len(known_x):
                    y_values.append(known_y[-1])
                else:
                    # Perform linear interpolation
                    x0, x1 = known_x[i - 1], known_x[i]
                    y0, y1 = known_y[i - 1], known_y[i]

                    # Linear interpolation formula
                    y = y0 + (x - x0) * (y1 - y0) / (x1 - x0)
                    y_values.append(y)

        return y_values

    def _format_comment(self, median_cdf: List[float], comments: list) -> str:
        """
        Format the final comment with all rationales.

        Args:
            median_cdf: The median CDF across all runs
            comments: List of individual comments

        Returns:
            Formatted comment string
        """
        final_comment_sections = [
            f"## Rationale {i+1}\n{comment}" for i, comment in enumerate(comments)
        ]

        final_comment = (
            f"Median CDF: `{str(median_cdf)[:100]}...`\n\n"
            + "\n\n".join(final_comment_sections)
        )

        return final_comment
