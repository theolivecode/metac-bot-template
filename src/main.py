"""
Main Entry Point for Forecasting Bot

This script orchestrates the forecasting process for Metaculus questions.
"""
import asyncio
import logging
from typing import List, Tuple

from .config import (
    api_config,
    bot_config,
    llm_config,
    metaculus_config,
    setup_logging,
    EXAMPLE_QUESTIONS,
    QuestionType,
)
from .api import MetaculusClient
from .research import LLMResearchProvider, PerplexityResearchProvider
from .forecasting import (
    BinaryForecaster,
    NumericForecaster,
    MultipleChoiceForecaster,
)
from .utils import LLMClient, LocalLLMClient, RateLimiter

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)


class ForecastingBot:
    """Main forecasting bot orchestrator."""

    def __init__(self, use_local_llm_for_forecasting: bool = True):
        """Initialize the forecasting bot with all necessary components."""
        # Initialize clients with shared rate limiter
        self.metaculus_client = MetaculusClient()
        shared_rate_limiter = RateLimiter(bot_config.concurrent_requests_limit)
        self.llm_client = LLMClient(rate_limiter=shared_rate_limiter, base_url=api_config.openrouter_base_url, api_key=api_config.openrouter_api_key)
        self.local_llm_client = LocalLLMClient(rate_limiter=shared_rate_limiter)
        forecasting_client = self.local_llm_client if use_local_llm_for_forecasting else self.llm_client

        # Initialize research provider
        # Priority: OpenAI/OpenRouter > Perplexity > AskNews
        if api_config.openrouter_api_key or api_config.openai_api_key:
            logger.info("Using LLM research provider")
            self.research_provider = LLMResearchProvider(llm_client=self.llm_client, model=bot_config.research_model, temperature=bot_config.research_temperature)
        elif api_config.perplexity_api_key:
            logger.info("Using Perplexity research provider")
            self.research_provider = PerplexityResearchProvider()

        # Initialize forecasters
        self.binary_forecaster = BinaryForecaster(llm_client=forecasting_client, research_provider=self.research_provider)
        self.numeric_forecaster = NumericForecaster(llm_client=forecasting_client, research_provider=self.research_provider)
        self.multiple_choice_forecaster = MultipleChoiceForecaster(llm_client=forecasting_client, research_provider=self.research_provider)


    async def forecast_question(
        self,
        question_id: int,
        post_id: int,
    ) -> str:
        """
        Forecast a single question.

        Args:
            question_id: The question ID
            post_id: The post ID

        Returns:
            Summary of the forecast
        """
        logger.info("=" * 60)
        logger.info(f"Forecasting Question {question_id} (Post {post_id})")
        logger.info("=" * 60)

        # Get post details
        post_details = self.metaculus_client.get_post_details(post_id)
        question_details = post_details["question"]

        title = question_details["title"]
        question_type = question_details["type"]

        logger.info(f"Title: {title}")
        logger.info(f"Type: {question_type}")
        logger.info(f"Resolution Criteria: {question_details.get('resolution_criteria', 'N/A')}")
        logger.info(f"Fine Print: {question_details.get('fine_print', 'N/A')}")

        summary = f"-----------------------------------------------\n"
        summary += f"Question: {title}\n"
        summary += f"URL: https://www.metaculus.com/questions/{post_id}/\n"

        # Check if already forecasted
        if (
            bot_config.skip_previously_forecasted_questions
            and self.metaculus_client.has_existing_forecast(post_details)
        ):
            summary += "Skipped: Forecast already made\n"
            logger.info("Skipping: Forecast already exists")
            return summary

        # Generate forecast based on question type
        try:
            if question_type == QuestionType.BINARY:
                forecast, comment = await self.binary_forecaster.forecast(
                    question_details, bot_config.num_runs_per_question
                )

            elif question_type == QuestionType.NUMERIC:
                forecast, comment = await self.numeric_forecaster.forecast(
                    question_details, bot_config.num_runs_per_question
                )

            elif question_type == QuestionType.DISCRETE:
                forecast, comment = await self.numeric_forecaster.forecast(
                    question_details, bot_config.num_runs_per_question
                )

            elif question_type == QuestionType.MULTIPLE_CHOICE:
                forecast, comment = await self.multiple_choice_forecaster.forecast(
                    question_details, bot_config.num_runs_per_question
                )

            else:
                raise ValueError(f"Unknown question type: {question_type}")

            logger.info("=" * 60)
            logger.info("Forecast Result:")
            logger.info(forecast)
            logger.info("=" * 60)

            # Format summary
            if question_type in [QuestionType.NUMERIC, QuestionType.DISCRETE]:
                summary += f"Forecast: {str(forecast)[:200]}...\n"
            else:
                summary += f"Forecast: {forecast}\n"

            summary += f"Comment:\n```\n{comment[:200]}...\n```\n\n"

            # Submit forecast if enabled
            if bot_config.submit_prediction:
                forecast_payload = self.metaculus_client.create_forecast_payload(
                    forecast, question_type
                )
                self.metaculus_client.post_prediction(question_id, forecast_payload)
                self.metaculus_client.post_comment(post_id, comment)
                summary += "Posted: Forecast was posted to Metaculus.\n"
                logger.info("Forecast submitted to Metaculus")

            return summary

        except Exception as e:
            logger.error(f"Error forecasting question {question_id}: {e}", exc_info=True)
            raise

    async def forecast_questions(
        self,
        question_id_post_id_pairs: List[Tuple[int, int]],
    ) -> None:
        """
        Forecast multiple questions.

        Args:
            question_id_post_id_pairs: List of (question_id, post_id) tuples
        """
        logger.info(f"Starting forecast for {len(question_id_post_id_pairs)} questions")

        # If using LocalLLMClient, wrap in async context manager
        if isinstance(self.llm_client, LocalLLMClient):
            async with self.llm_client:
                forecast_tasks = [
                    self.forecast_question(question_id, post_id)
                    for question_id, post_id in question_id_post_id_pairs
                ]
                forecast_summaries = await asyncio.gather(*forecast_tasks, return_exceptions=True)
        else:
            forecast_tasks = [
                self.forecast_question(question_id, post_id)
                for question_id, post_id in question_id_post_id_pairs
            ]
            forecast_summaries = await asyncio.gather(*forecast_tasks, return_exceptions=True)

        # Print summaries
        print("\n" + "#" * 100)
        print("Forecast Summaries")
        print("#" * 100 + "\n")

        errors = []
        for (question_id, post_id), forecast_summary in zip(
            question_id_post_id_pairs, forecast_summaries
        ):
            if isinstance(forecast_summary, Exception):
                error_msg = (
                    f"-----------------------------------------------\n"
                    f"Post {post_id} Question {question_id}:\n"
                    f"Error: {forecast_summary.__class__.__name__} {forecast_summary}\n"
                    f"URL: https://www.metaculus.com/questions/{post_id}/\n"
                )
                print(error_msg)
                logger.error(error_msg)
                errors.append(forecast_summary)
            else:
                print(forecast_summary)

        if errors:
            error_message = f"Errors were encountered: {errors}"
            logger.error(error_message)
            raise RuntimeError(error_message)

        logger.info("All forecasts completed successfully")


async def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("Metaculus Forecasting Bot - Refactored Version")
    logger.info("=" * 60)

    # Initialize bot
    bot = ForecastingBot(use_local_llm_for_forecasting=False)

    # Get questions to forecast
    if bot_config.use_example_questions:
        logger.info("Using example questions")
        question_id_post_id_pairs = EXAMPLE_QUESTIONS
    else:
        logger.info(f"Fetching questions from tournament: {metaculus_config.default_tournament_id}")
        question_id_post_id_pairs = (
            bot.metaculus_client.get_open_question_ids_from_tournament()
        )

    # Display configuration
    logger.info("=" * 60)
    logger.info(f"Questions to forecast: {question_id_post_id_pairs}")
    logger.info(f"Submit predictions: {bot_config.submit_prediction}")
    logger.info(f"Runs per question: {bot_config.num_runs_per_question}")
    logger.info(f"Skip previously forecasted: {bot_config.skip_previously_forecasted_questions}")
    logger.info("=" * 60)

    # Run forecasts
    await bot.forecast_questions(question_id_post_id_pairs)


if __name__ == "__main__":
    # python -m src.main
    # poetry run python -m src.main
    asyncio.run(main())
