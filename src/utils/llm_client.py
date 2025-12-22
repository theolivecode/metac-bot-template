"""
LLM Client

Base class and implementations for calling LLM APIs with rate limiting and error handling.
"""
import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict

import aiohttp
from openai import AsyncOpenAI

from ..config import api_config, bot_config, llm_config

logger = logging.getLogger(__name__)


class RateLimiter:
    """Shared rate limiting utility for LLM clients."""

    def __init__(self, concurrent_limit: int):
        """
        Initialize rate limiter.

        Args:
            concurrent_limit: Maximum number of concurrent requests.
        """
        self.semaphore = asyncio.Semaphore(concurrent_limit)

    async def __aenter__(self):
        """Acquire semaphore."""
        await self.semaphore.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Release semaphore."""
        self.semaphore.release()


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    def __init__(self, rate_limiter: Optional[RateLimiter] = None):
        """
        Initialize the base LLM client.

        Args:
            rate_limiter: Shared rate limiter. If None, creates a new one.
        """
        self.rate_limiter = rate_limiter or RateLimiter(
            bot_config.concurrent_requests_limit
        )

    @abstractmethod
    async def call(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Make a completion request to the LLM.

        Args:
            prompt: The prompt to send
            model: Model to use. If None, uses default from config.
            temperature: Temperature setting. If None, uses default from config.

        Returns:
            The LLM's response text

        Raises:
            ValueError: If no response is returned
        """
        pass


class LLMClient(BaseLLMClient):
    """Client for making API-based LLM calls (OpenAI, OpenRouter, etc.) with rate limiting."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        """
        Initialize the LLM client.

        Args:
            base_url: Base URL for the API. If None, uses config.
            api_key: API key. If None, uses config.
            rate_limiter: Shared rate limiter. If None, creates a new one.
        """
        super().__init__(rate_limiter)

        self.base_url = base_url or api_config.openrouter_base_url
        self.api_key = api_key or api_config.openrouter_api_key

        self.client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            max_retries=llm_config.max_retries,
        )

    async def call(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Make a completion request to the LLM API.

        Args:
            prompt: The prompt to send
            model: Model to use. If None, uses default from config.
            temperature: Temperature setting. If None, uses default from config.

        Returns:
            The LLM's response text

        Raises:
            ValueError: If no response is returned
        """
        if model is None:
            model = bot_config.default_model

        if temperature is None:
            temperature = bot_config.default_temperature

        logger.info(f"Calling API LLM with model={model}, temperature={temperature}")

        async with self.rate_limiter:
            # Some models don't support temperature parameter
            if self.base_url == api_config.local_llm_base_url:
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=llm_config.local_llm_max_tokens,
                    temperature=temperature,
                    stream=False,
                )
            elif model in llm_config.models_without_temperature:
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    stream=False,
                )
            else:
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    stream=False,
                )

            answer = response.choices[0].message.content

            if answer is None:
                logger.error("No answer returned from LLM")
                raise ValueError("No answer returned from LLM")

            logger.debug(f"LLM response received (length: {len(answer)} chars)")
            return answer


class LocalLLMClient(BaseLLMClient):
    """
    Client for making calls to a local LLM API.

    Works exactly like LLMClient - just instantiate and use:

    client = LocalLLMClient()
    response = await client.call("prompt")

    The aiohttp session is created automatically and cleaned up on garbage collection.
    For explicit cleanup, call await client.close() when done.
    """

    def __init__(self, rate_limiter: Optional[RateLimiter] = None):
        """
        Initialize the local LLM client.

        Args:
            rate_limiter: Shared rate limiter. If None, creates a new one.
        """
        super().__init__(rate_limiter)
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """
        Get or create the aiohttp session.

        Returns:
            Active aiohttp.ClientSession
        """
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            logger.debug("Created new aiohttp session for LocalLLMClient")
        return self._session

    async def close(self):
        """
        Close the aiohttp session.

        Optional - call this to explicitly clean up resources.
        The session will be automatically closed when the object is garbage collected.

        Example:
            client = LocalLLMClient()
            response = await client.call("prompt")
            await client.close()  # Explicit cleanup
        """
        if self._session and not self._session.closed:
            await self._session.close()
            logger.debug("Closed aiohttp session for LocalLLMClient")
            self._session = None

    def __del__(self):
        """
        Cleanup on garbage collection.

        Note: This attempts cleanup but async cleanup in __del__ is not ideal.
        For guaranteed cleanup, call close() explicitly.
        """
        if self._session and not self._session.closed:
            try:
                # Try to close the session - best effort
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.close())
                else:
                    loop.run_until_complete(self.close())
            except Exception:
                # Best effort cleanup - don't let exceptions propagate from __del__
                pass

    async def call(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Make a completion request to the local LLM API.

        Args:
            prompt: The prompt to send
            model: Model to use. If None, uses default from config.
            temperature: Temperature setting. If None, uses default from config.

        Returns:
            The LLM's response text

        Raises:
            ValueError: If no response is returned after all retries
        """
        # Ensure we have a session
        session = await self._get_session()

        if model is None:
            model = llm_config.local_llm_model

        if temperature is None:
            temperature = llm_config.local_llm_temperature

        use_think_str = "No Think" if llm_config.local_llm_no_think else "Think"
        logger.info(f"Calling Local LLM with model={model} ({use_think_str}), temperature={temperature}")

        # Add no_think directive if configured
        if llm_config.local_llm_no_think:
            prompt += "\n\\no_think\n"

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": llm_config.local_llm_max_tokens,
            "temperature": llm_config.local_llm_temperature,
        }

        last_error = None

        async with self.rate_limiter:
            for attempt in range(llm_config.local_llm_max_retries):
                try:
                    response = await self._post(
                        session,
                        f"{api_config.local_llm_base_url}/chat/completions",
                        payload
                    )
                    answer = response["choices"][0]["message"]["content"].strip()

                    # Log token usage if available
                    if "usage" in response:
                        token_usage = response["usage"]
                        logger.info(f"Token usage: {token_usage}")

                    logger.debug(f"Local LLM response received (length: {len(answer)} chars)")
                    return answer

                except Exception as e:
                    last_error = e
                    logger.error(
                        f"Error in Local LLM call (attempt {attempt+1}/{llm_config.local_llm_max_retries}): {e}"
                    )

        raise ValueError(
            f"Failed to get response from Local LLM after {llm_config.local_llm_max_retries} attempts. "
            f"Last error: {last_error}"
        )

    async def _post(
        self, session: aiohttp.ClientSession, url: str, data: Dict
    ) -> Dict:
        """
        POST JSON request.

        Args:
            session: The aiohttp session to use
            url: The URL to POST to
            data: The JSON payload

        Returns:
            The parsed JSON response

        Raises:
            RuntimeError: If request fails or returns non-JSON
        """
        async with session.post(url, json=data) as resp:
            raw = await resp.text()
            if resp.status >= 400:
                raise RuntimeError(f"{url} → {resp.status}: {raw[:200]}")

            try:
                return json.loads(raw)
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    f"{url} sent non-JSON response "
                    f"(content-type={resp.headers.get('Content-Type')})"
                ) from exc
