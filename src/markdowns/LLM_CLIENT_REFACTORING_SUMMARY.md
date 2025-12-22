# LLM Client Refactoring Summary

## Overview

This document summarizes the refactoring of the LLM client architecture to use a base class pattern, allowing for both API-based and local LLM implementations with a unified interface.

## Changes Made

### 1. Configuration (`src/config.py`)

**Added new `LLMConfig` dataclass** to centralize all LLM-related configuration:

```python
@dataclass
class LLMConfig:
    # API-based LLM settings
    max_retries: int = 5
    models_without_temperature: list = None  # Auto-initialized in __post_init__

    # Local LLM settings
    local_llm_model: str = "Qwen/Qwen3-32B"
    local_llm_max_tokens: int = 7000
    local_llm_temperature: float = 0.2
    local_llm_max_retries: int = 3
    local_llm_no_think: bool = False
```

**Key Benefits:**
- All LLM settings in one place
- Easy to modify without touching code
- Can be overridden via environment variables
- Type-safe with dataclasses

### 2. LLM Client (`src/utils/llm_client.py`)

**Complete rewrite with base class architecture:**

```python
BaseLLMClient (ABC)
├── LLMClient (API-based)
└── LocalLLMClient (Local server)
```

#### BaseLLMClient (Abstract Base Class)

```python
class BaseLLMClient(ABC):
    @abstractmethod
    async def call(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        pass
```

**Key Features:**
- Defines the interface all LLM clients must implement
- Ensures consistent API across implementations
- Allows polymorphic usage in forecasters and research providers

#### LLMClient (API-Based)

```python
class LLMClient(BaseLLMClient):
    # For OpenAI, OpenRouter, etc.
    # Uses AsyncOpenAI client
```

**Key Features:**
- Supports any OpenAI-compatible API
- Configurable via `api_config.openrouter_*`
- Auto-handles models without temperature support
- Rate limiting built-in

#### LocalLLMClient (Local Server)

```python
class LocalLLMClient(BaseLLMClient):
    # For local LLM servers (vLLM, llama.cpp, etc.)
    # Uses aiohttp
```

**Key Features:**
- Direct HTTP API calls via aiohttp
- Requires async context manager (`async with`)
- Configurable via `llm_config.local_llm_*`
- Supports custom directives (e.g., `\no_think`)
- Rate limiting built-in

### 3. Research Provider (`src/research/llm.py`)

**Updated to accept `BaseLLMClient`:**

```python
class LLMResearchProvider(ResearchProvider):
    def __init__(
        self,
        llm_client: Optional[BaseLLMClient] = None,  # Changed from LLMClient
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ):
        self.llm_client = llm_client or LLMClient()
```

**Benefits:**
- Can now accept any LLM client (API or local)
- More flexible and extensible
- Same interface, more options

### 4. Forecasters

**All forecasters updated to accept `BaseLLMClient`:**

#### BinaryForecaster (`src/forecasting/binary.py`)
```python
class BinaryForecaster:
    def __init__(
        self,
        llm_client: BaseLLMClient,  # Changed from LLMClient
        research_provider: ResearchProvider,
    ):
```

#### NumericForecaster (`src/forecasting/numeric.py`)
```python
class NumericForecaster:
    def __init__(
        self,
        llm_client: BaseLLMClient,  # Changed from LLMClient
        research_provider: ResearchProvider,
    ):
```

#### MultipleChoiceForecaster (`src/forecasting/multiple_choice.py`)
```python
class MultipleChoiceForecaster:
    def __init__(
        self,
        llm_client: BaseLLMClient,  # Changed from LLMClient
        research_provider: ResearchProvider,
    ):
```

**Benefits:**
- Can use either API-based or local LLM
- No code changes needed to switch
- Just pass a different client instance

### 5. Utilities Export (`src/utils/__init__.py`)

**Updated exports:**

```python
from .llm_client import BaseLLMClient, LLMClient, LocalLLMClient, RateLimiter

__all__ = [
    "BaseLLMClient",  # Added
    "LLMClient",
    "LocalLLMClient",  # Added
    "RateLimiter",  # Added
    ...
]
```

### 6. Documentation

**Created comprehensive documentation:**

1. **`src/utils/LLM_CLIENT_README.md`** - Complete architecture documentation
2. **`src/utils/llm_client_example.py`** - Working code examples
3. **This file** - Summary of changes

## Usage Examples

### Using API-Based Client (Default)

```python
from src.utils import LLMClient

client = LLMClient()
response = await client.call("What is 2+2?")
```

### Using Local LLM Client

```python
from src.utils import LocalLLMClient

local_llm_client = LLMClient()
response = await local_llm_client.call("What is 2+2?")
```

### Switching Between Clients (No Code Changes Needed)

```python
from src.utils import BaseLLMClient, LLMClient, LocalLLMClient
from src.research import LLMResearchProvider

# Use API-based
api_client = LLMClient()
research_provider = LLMResearchProvider(llm_client=api_client)

# OR use local (same interface!)
local_llm_client = LLMClient()
research_provider = LLMResearchProvider(llm_client=local_llm_client)
```

### In Forecasters

```python
from src.forecasting import BinaryForecaster
from src.utils import LLMClient, LocalLLMClient

# With API client
api_client = LLMClient()
forecaster = BinaryForecaster(api_client, research_provider)

# With local client
local_llm_client = LocalLLMClient()
forecaster = BinaryForecaster(local_llm_client, research_provider)
```

## Migration Guide

### For Existing Code

**Before:**
```python
from src.utils import LLMClient

client = LLMClient()
# Used only API-based LLMs
```

**After:**
```python
from src.utils import LLMClient, LocalLLMClient

# Option 1: Use API-based (same as before)
client = LLMClient()

# Option 2: Use local LLM (new!)
local_llm_client = LocalLLMClient()
```

### For Research Providers

**No changes needed!** The research provider automatically works with both:

```python
# Works with API client
research = LLMResearchProvider(llm_client=LLMClient())

# Also works with local client
research = LLMResearchProvider(llm_client=LocalLLMClient())
```

### For Forecasters

**No changes needed!** Forecasters automatically work with both:

```python
# Works with API client
forecaster = BinaryForecaster(LLMClient(), research_provider)

# Also works with local client
forecaster = BinaryForecaster(LocalLLMClient(), research_provider)
```

## Key Benefits

### 1. **Flexibility**
- Easy to switch between API and local LLMs
- No code changes needed
- Just swap the client instance

### 2. **Extensibility**
- Want to add a new LLM provider? Just extend `BaseLLMClient`
- All existing code works automatically

### 3. **Configuration-Driven**
- All settings in `config.py`
- No hardcoded values
- Easy to customize

### 4. **Type Safety**
- Abstract base class enforces the interface
- Type hints throughout
- Better IDE support

### 5. **Testability**
- Easy to mock `BaseLLMClient` for testing
- Can create test implementations
- Polymorphic design enables testing

### 6. **Maintainability**
- Clear separation of concerns
- Each client handles its own protocol
- Shared interface reduces duplication

## Files Changed

1. **`src/config.py`** - Added `LLMConfig` dataclass
2. **`src/utils/llm_client.py`** - Complete rewrite with base class
3. **`src/utils/__init__.py`** - Updated exports
4. **`src/research/llm.py`** - Updated to use `BaseLLMClient`
5. **`src/forecasting/binary.py`** - Updated to use `BaseLLMClient`
6. **`src/forecasting/numeric.py`** - Updated to use `BaseLLMClient`
7. **`src/forecasting/multiple_choice.py`** - Updated to use `BaseLLMClient`

## New Files Created

1. **`src/utils/LLM_CLIENT_README.md`** - Complete documentation
2. **`src/utils/llm_client_example.py`** - Working examples
3. **`LLM_CLIENT_REFACTORING_SUMMARY.md`** - This file

## Testing

All modules compile successfully:
```bash
python -m py_compile src/config.py \
    src/utils/llm_client.py \
    src/utils/__init__.py \
    src/research/llm.py \
    src/forecasting/binary.py \
    src/forecasting/numeric.py \
    src/forecasting/multiple_choice.py \
    src/main.py
```

✅ **All checks passed**

## Next Steps

1. **Update main.py** if needed to use local clients
2. **Test with local LLM server** (vLLM, llama.cpp, etc.)
3. **Add more client implementations** if needed (e.g., Anthropic direct API)
4. **Write unit tests** for each client
5. **Update README** with new capabilities

## Questions?

See:
- **`src/utils/LLM_CLIENT_README.md`** - Full architecture documentation
- **`src/utils/llm_client_example.py`** - Working code examples
- **`src/config.py`** - Configuration options
