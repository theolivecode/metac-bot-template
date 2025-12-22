# LLM Client Architecture

This document explains the LLM client architecture and how to use it.

## Overview

The LLM client module provides a unified interface for calling both API-based LLMs (like OpenAI, OpenRouter) and local LLMs. All clients share the same interface through a base class, making it easy to swap between different LLM providers.

## Architecture

```
BaseLLMClient (Abstract Base Class)
├── LLMClient (API-based: OpenAI, OpenRouter, etc.)
└── LocalLLMClient (Local LLM server)
```

## Key Features

1. **Unified Interface**: Both clients use the same `call(prompt, model, temperature)` signature
2. **Configuration-Driven**: All settings are in `config.py`
3. **Rate Limiting**: Built-in concurrent request limiting
4. **Error Handling**: Automatic retries and proper error messages
5. **Type Safety**: Full type hints and abstract base class

## Configuration

All LLM client settings are in `src/config.py`:

```python
@dataclass
class LLMConfig:
    # API-based LLM settings
    max_retries: int = 5
    models_without_temperature: list = ["o4-mini-deep-research", "anthropic/claude-sonnet-4.5"]

    claude_sonnet_45 = "anthropic/claude-sonnet-4.5"
    o4_mini_deep_search = "o4-mini-deep-research"

    # Local LLM settings
    local_llm_model: str = "Qwen/Qwen3-32B"
    local_llm_max_tokens: int = 7000
    local_llm_temperature: float = 0.2
    local_llm_max_retries: int = 3
    local_llm_no_think: bool = False
```

### Environment Variables

```bash
# For API-based LLM
export OPENROUTER_API_KEY="your_key"
export OPENROUTER_BASE_URL="https://openrouter.ai/api/v1"

# For Local LLM
export LOCAL_LLM_BASE_URL="http://localhost:8000"
```

## Usage

### API-Based LLM Client

```python
from src.utils import LLMClient

# Create client
client = LLMClient()

# Simple call (uses defaults from config)
response = await client.call("What is 2+2?")

# Call with specific parameters
response = await client.call(
    prompt="Explain quantum computing",
    model="anthropic/claude-sonnet-4.5",
    temperature=0.7
)
```

### Local LLM Client

```python
from src.utils import LocalLLMClient

# Must use async context manager
async with LocalLLMClient() as client:
    # Simple call (uses defaults from config)
    response = await client.call("What is 2+2?")

    # Call with specific parameters
    response = await client.call(
        prompt="Explain quantum computing",
        model="Qwen/Qwen3-32B",  # or use default from config
        temperature=0.5
    )
```

### Shared Interface

Both clients implement the same interface, so you can write code that works with either:

```python
async def get_prediction(client: BaseLLMClient, question: str) -> str:
    """Works with any LLM client."""
    return await client.call(f"Forecast: {question}", temperature=0.3)

# Use with API client
api_client = LLMClient()
result = await get_prediction(api_client, "Will it rain?")

# Use with local client
async with LocalLLMClient() as local_client:
    result = await get_prediction(local_client, "Will it rain?")
```

### Shared Rate Limiter

You can share a rate limiter between multiple clients:

```python
from src.utils import RateLimiter, LLMClient, LocalLLMClient

# Create shared rate limiter (max 3 concurrent requests total)
rate_limiter = RateLimiter(concurrent_limit=3)

# All clients share the same rate limiter
client1 = LLMClient(rate_limiter=rate_limiter)
client2 = LLMClient(rate_limiter=rate_limiter)

async with LocalLLMClient(rate_limiter=rate_limiter) as client3:
    # These 4 requests will be limited to 3 concurrent
    tasks = [
        client1.call("Q1"),
        client2.call("Q2"),
        client3.call("Q3"),
        client1.call("Q4"),  # Waits for one above to finish
    ]
    results = await asyncio.gather(*tasks)
```

## Call Signature

Both clients use the same signature:

```python
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
    """
```

### Parameters

- **`prompt`** (required): The text prompt to send to the LLM
- **`model`** (optional):
  - For `LLMClient`: Model identifier (e.g., "anthropic/claude-sonnet-4.5")
  - For `LocalLLMClient`: Local model name (e.g., "Qwen/Qwen3-32B")
  - If `None`, uses default from config
- **`temperature`** (optional):
  - Sampling temperature (0.0 to 1.0+)
  - Lower = more focused, higher = more creative
  - If `None`, uses default from config
  - Some models don't support temperature (auto-handled)

## Key Differences Between Clients

| Feature | LLMClient | LocalLLMClient |
|---------|-----------|----------------|
| **Base URL** | From `api_config.openrouter_base_url` | From `api_config.local_llm_base_url` |
| **API Key** | Required (from `api_config.openrouter_api_key`) | Not needed |
| **Context Manager** | Not required | **Required** (`async with`) |
| **HTTP Client** | Uses `openai.AsyncOpenAI` | Uses `aiohttp.ClientSession` |
| **Max Tokens** | Determined by model | Set in config (`local_llm_max_tokens`) |
| **Special Features** | Auto-detects models without temperature support | Can add `\no_think` directive |

## Implementation Details

### BaseLLMClient

Abstract base class defining the interface:

```python
class BaseLLMClient(ABC):
    def __init__(self, rate_limiter: Optional[RateLimiter] = None):
        self.rate_limiter = rate_limiter or RateLimiter(...)

    @abstractmethod
    async def call(self, prompt, model, temperature) -> str:
        pass
```

### LLMClient

API-based implementation:
- Uses OpenAI SDK
- Supports any OpenAI-compatible API (OpenRouter, etc.)
- Auto-handles models that don't support temperature
- Configurable max retries
- Rate limited

### LocalLLMClient

Local LLM implementation:
- Uses aiohttp for HTTP requests
- Requires async context manager for session management
- Supports local LLM servers (like vLLM, llama.cpp)
- Configurable max tokens, retries, and special directives
- Rate limited

## Error Handling

Both clients provide comprehensive error handling:

```python
try:
    response = await client.call("prompt")
except ValueError as e:
    # No response returned after retries
    print(f"LLM error: {e}")
except RuntimeError as e:
    # API error (for LocalLLMClient)
    print(f"API error: {e}")
```

## Logging

Both clients use Python's logging module:

```python
import logging

# Set logging level
logging.basicConfig(level=logging.DEBUG)

# LLM clients will log:
# - DEBUG: Request/response details
# - INFO: Token usage (LocalLLMClient)
# - ERROR: Failures and retries
```

## Best Practices

1. **Use defaults**: Let config handle model and temperature unless you need to override
2. **Share rate limiters**: When using multiple clients, share a rate limiter
3. **Context managers**: Always use `async with` for LocalLLMClient
4. **Error handling**: Wrap calls in try/except for production code
5. **Type hints**: Use `BaseLLMClient` as the type for functions that accept any client

## Migration from Old Code

If you have old code using the previous interface:

```python
# Old code
llm_client = LLMClient()
response = await call_llm(prompt, model, temperature)

# New code (API-based)
llm_client = LLMClient()
response = await llm_client.call(prompt, model, temperature)

# New code (Local)
async with LocalLLMClient() as llm_client:
    response = await llm_client.call(prompt, model, temperature)
```

## Examples

See `llm_client_example.py` for complete working examples.
