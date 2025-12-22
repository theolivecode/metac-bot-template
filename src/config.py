"""
Configuration and Constants for the Forecasting Bot
"""
import logging
import os
from dataclasses import dataclass, field
from typing import Optional

import dotenv

# Load environment variables
dotenv.load_dotenv()


@dataclass
class APIConfig:
    """API configuration settings."""

    metaculus_token: Optional[str] = os.getenv("METACULUS_TOKEN")
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    openrouter_api_key: Optional[str] = os.getenv("OPENROUTER_API_KEY")
    openrouter_base_url: Optional[str] = os.getenv("OPENROUTER_BASE_URL")
    perplexity_api_key: Optional[str] = os.getenv("PERPLEXITY_API_KEY")
    asknews_client_id: Optional[str] = os.getenv("ASKNEWS_CLIENT_ID")
    asknews_secret: Optional[str] = os.getenv("ASKNEWS_SECRET")
    exa_api_key: Optional[str] = os.getenv("EXA_API_KEY")
    local_llm_base_url: Optional[str] = os.getenv("LOCAL_LLM_BASE_URL")


@dataclass
class BotConfig:
    """Bot behavior configuration."""

    submit_prediction: bool = True
    use_example_questions: bool = False
    num_runs_per_question: int = 1
    skip_previously_forecasted_questions: bool = True
    concurrent_requests_limit: int = 5
    default_model: str = "openai/gpt-5.2"
    default_temperature: float = 0.3
    research_model: str = "openai/o4-mini-deep-research"
    research_temperature: float = 0.3


@dataclass
class LLMConfig:
    """LLM client configuration."""

    # API-based LLM settings
    max_retries: int = 5
    models_without_temperature: list[str] = field(
        default_factory=lambda: ["openai/o4-mini-deep-research", "anthropic/claude-sonnet-4.5"]
    )

    claude_sonnet_45 = "anthropic/claude-sonnet-4.5"
    claude_opus_45 = "anthropic/claude-opus-4.5"
    o4_mini_deep_search = "openai/o4-mini-deep-research"
    gpt_52 = "openai/gpt-5.2"
    gemini_25_flash = "google/gemini-2.5-flash"
    
    # Local LLM settings
    local_llm_model: str = "Qwen/Qwen3-32B"
    local_llm_max_tokens: int = 5000
    local_llm_temperature: float = 0.2
    local_llm_max_retries: int = 3
    local_llm_no_think: bool = False 

@dataclass
class MetaculusConfig:
    """Metaculus-specific configuration."""

    api_base_url: str = "https://www.metaculus.com/api"

    # Tournament IDs
    q4_2024_ai_benchmarking_id: int = 32506
    q1_2025_ai_benchmarking_id: int = 32627
    fall_2025_ai_benchmarking_id: str = "fall-aib-2025"
    current_minibench_id: str = "minibench"
    q4_2024_quarterly_cup_id: int = 3672
    q1_2025_quarterly_cup_id: int = 32630
    current_metaculus_cup_id: str = "metaculus-cup"
    axc_2025_tournament_id: int = 32564
    ai_2027_tournament_id: str = "ai-2027"

    # Default tournament to use
    default_tournament_id: str = "fall-aib-2025"


# Example questions for testing
EXAMPLE_QUESTIONS = [
    # (question_id, post_id)
    # (578, 578),  # Human Extinction - Binary
    # (14333, 14333),  # Age of Oldest Human - Numeric
    (22427, 22427),  # Number of New Leading AI Labs - Multiple Choice
    # (38195, 38880),  # Number of US Labor Strikes Due to AI in 2029 - Discrete
]

# Question type constants
class QuestionType:
    """Question type constants."""
    BINARY = "binary"
    NUMERIC = "numeric"
    DISCRETE = "discrete"
    MULTIPLE_CHOICE = "multiple_choice"

@dataclass
class LoggingConfig:
    """Logging configuration."""

    # Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Whether to log to file
    log_to_file: bool = False
    log_file_path: str = "forecasting_bot.log"




# Global configuration instances
api_config = APIConfig()
bot_config = BotConfig()
logging_config = LoggingConfig()
llm_config = LLMConfig()
metaculus_config = MetaculusConfig()


def setup_logging(level: Optional[str] = None, log_to_file: Optional[bool] = None):
    """
    Setup logging configuration.

    This function can be called from anywhere to initialize logging.
    It's automatically called by main.py, but can also be called manually
    for standalone usage (e.g., in examples or tests).

    Args:
        level: Log level override (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to file (overrides config)
    """
    # Use provided level or fall back to config
    log_level_str = level or logging_config.log_level
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)

    # Use provided log_to_file or fall back to config
    should_log_to_file = log_to_file if log_to_file is not None else logging_config.log_to_file

    # Setup handlers
    handlers = []

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(logging_config.log_format))
    handlers.append(console_handler)

    # Optional file handler
    if should_log_to_file:
        file_handler = logging.FileHandler(logging_config.log_file_path)
        file_handler.setFormatter(logging.Formatter(logging_config.log_format))
        handlers.append(file_handler)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=logging_config.log_format,
        handlers=handlers,
        force=True,  # Override any existing configuration
    )

    # Suppress httpx noise
    # logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpx").disabled = True

    logging.info(f"Logging configured: level={log_level_str}, log_to_file={should_log_to_file}")
