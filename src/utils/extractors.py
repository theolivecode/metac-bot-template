"""
Response Extractors

Functions to extract structured data from LLM responses.
"""
import logging
import re
from typing import Dict, List

logger = logging.getLogger(__name__)


def extract_probability_percentage(forecast_text: str) -> float:
    """
    Extract a probability percentage from forecast text.

    Looks for patterns like "Probability: XX%" and returns as a decimal (0.01 to 0.99).

    Args:
        forecast_text: The text containing the probability

    Returns:
        Probability as a decimal (clamped between 0.01 and 0.99)

    Raises:
        ValueError: If no probability can be extracted
    """
    matches = re.findall(r"(\d+)%", forecast_text)

    if matches:
        # Return the last number found before a '%'
        number = int(matches[-1])
        number = min(99, max(1, number))  # Clamp between 1 and 99
        logger.debug(f"Extracted probability: {number}%")
        return number / 100

    logger.error(f"Could not extract probability from: {forecast_text[:200]}")
    raise ValueError(f"Could not extract prediction from response: {forecast_text}")


def extract_percentiles(forecast_text: str) -> Dict[int, float]:
    """
    Extract percentile values from forecast text.

    Looks for lines like "Percentile 10: XX" and extracts the values.

    Args:
        forecast_text: The text containing percentiles

    Returns:
        Dictionary mapping percentile numbers to values

    Raises:
        ValueError: If no percentiles can be extracted
    """
    pattern = r"^.*(?:P|p)ercentile.*$"
    number_pattern = r"-\s*(?:[^\d\-]*\s*)?(\d+(?:,\d{3})*(?:\.\d+)?)|(\d+(?:,\d{3})*(?:\.\d+)?)"
    results = []

    for line in forecast_text.split("\n"):
        if re.match(pattern, line):
            numbers = re.findall(number_pattern, line)
            numbers_no_commas = [
                next(num for num in match if num).replace(",", "") for match in numbers
            ]
            numbers = [
                float(num) if "." in num else int(num) for num in numbers_no_commas
            ]

            if len(numbers) > 1:
                first_number = numbers[0]
                last_number = numbers[-1]

                # Check if the original line had a negative sign before the last number
                if "-" in line.split(":")[-1]:
                    last_number = -abs(last_number)

                results.append((first_number, last_number))

    # Convert results to dictionary
    percentile_values = {}
    for first_num, second_num in results:
        key = int(first_num)
        percentile_values[key] = second_num

    if len(percentile_values) > 0:
        logger.debug(f"Extracted {len(percentile_values)} percentiles")
        return percentile_values

    logger.error(f"Could not extract percentiles from: {forecast_text[:200]}")
    raise ValueError(f"Could not extract prediction from response: {forecast_text}")


def extract_option_probabilities(
    forecast_text: str, num_options: int
) -> List[float]:
    """
    Extract probability values for multiple choice options.

    Extracts the last `num_options` numbers from the forecast text.

    Args:
        forecast_text: The text containing option probabilities
        num_options: Number of options to extract

    Returns:
        List of probability values (as percentages or decimals)

    Raises:
        ValueError: If insufficient probabilities can be extracted
    """
    # Number extraction pattern
    number_pattern = r"-?\d+(?:,\d{3})*(?:\.\d+)?"
    results = []

    # Iterate through each line in the text
    for line in forecast_text.split("\n"):
        # Extract all numbers from the line
        numbers = re.findall(number_pattern, line)
        numbers_no_commas = [num.replace(",", "") for num in numbers]

        # Convert strings to float or int
        numbers = [float(num) if "." in num else int(num) for num in numbers_no_commas]

        # Add the last number from each line if it exists
        if len(numbers) >= 1:
            last_number = numbers[-1]
            results.append(last_number)

    if len(results) >= num_options:
        # Return the last num_options items
        extracted = results[-num_options:]
        logger.debug(f"Extracted {len(extracted)} option probabilities")
        return extracted

    logger.error(f"Could not extract {num_options} probabilities from: {forecast_text[:200]}")
    raise ValueError(f"Could not extract prediction from response: {forecast_text}")
