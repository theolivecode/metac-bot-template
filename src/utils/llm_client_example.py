"""
Example usage of LLMClient and LocalLLMClient

Both clients share the same interface through BaseLLMClient.
"""
import asyncio
from ..config import setup_logging
from .llm_client import LLMClient, LocalLLMClient

# Configure logging for the examples
setup_logging(level="INFO")  # Set to DEBUG to see all logs


async def example_api_client():
    """Example using API-based LLMClient (OpenAI, OpenRouter, etc.)"""
    client = LLMClient()

    # Simple call with defaults from config
    response = await client.call("What is 2+2?")
    print(f"API LLM Response: {response}")

    # Call with specific model and temperature
    # response = await client.call(
    #     "Explain AI Forecasting",
    #     model="anthropic/claude-sonnet-4.5",
    #     temperature=0.7
    # )
    print(f"API LLM Response: {response}")


async def example_local_client():
    """Example using LocalLLMClient - works exactly like LLMClient!"""

    # Simple usage - just instantiate and use!
    client = LocalLLMClient()

    # Simple call with defaults from config
    Q1 = "What is 2+2?"
    response = await client.call(Q1)
    print(f"Question: {Q1}")
    print(f"Local LLM Response: {response}")

    # Call with specific temperature
    Q2 = "Explain AI Forecasting"
    response = await client.call(Q2, temperature=0.5)
    print(f"Question: {Q2}")
    print(f"Local LLM Response: {response}")

    # Optional: Explicit cleanup when done
    # await client.close()


async def example_shared_interface():
    """
    Example showing how both clients share the same interface.

    This allows you to swap between API and local LLMs easily.
    """
    # Function that works with any LLM client
    async def get_forecast(client, question: str) -> str:
        """Get a forecast from any LLM client."""
        prompt = f"Forecast the probability of: {question}"
        return await client.call(prompt, temperature=0.3)

    # Use with API client
    api_client = LLMClient()
    result = await get_forecast(api_client, "Will it rain tomorrow?")
    print(f"API Forecast: {result}")

    # Use with local client (same function! - no async with needed)
    local_client = LocalLLMClient()
    result = await get_forecast(local_client, "Will it rain tomorrow?")
    print(f"Local Forecast: {result}")


async def example_shared_rate_limiter():
    """
    Example using a shared rate limiter between multiple clients.

    This ensures all clients together don't exceed the concurrent request limit.
    """
    from .llm_client import RateLimiter

    # Create a shared rate limiter (max 3 concurrent requests)
    rate_limiter = RateLimiter(concurrent_limit=3)

    # Create multiple clients sharing the same rate limiter
    client1 = LLMClient(rate_limiter=rate_limiter)
    client2 = LLMClient(rate_limiter=rate_limiter)
    client3 = LocalLLMClient(rate_limiter=rate_limiter)  # No async with needed!

    # These will be rate-limited together (max 3 concurrent)
    tasks = [
        client1.call("Question 1"),
        client2.call("Question 2"),
        client3.call("Question 3"),
        client1.call("Question 4"),  # Will wait for one of the above to finish
    ]
    results = await asyncio.gather(*tasks)
    print(f"All results: {results}")


if __name__ == "__main__":
    print("=" * 60)
    print("LLM Client Examples")
    print("=" * 60)

    # Run examples
    # python -m src.utils.llm_client_example
    # Note: These examples assume you have properly configured
    # environment variables in your .env file

    # asyncio.run(example_api_client())
    asyncio.run(example_local_client())
    # asyncio.run(example_shared_interface())
    # asyncio.run(example_shared_rate_limiter())

    print("")
    print("-"*60)
    print("Examples are commented out. Uncomment to run them.")
    print("Make sure you have configured your API keys in .env file.")
