# LLM Client Architecture Diagram

## Class Hierarchy

```
┌─────────────────────────────────────────────────────────┐
│                    BaseLLMClient (ABC)                  │
│                                                         │
│  + __init__(rate_limiter)                               │
│  + call(prompt, model, temperature) -> str  [abstract]  │
└─────────────────────────────────────────────────────────┘
                          ▲
                          │
                          │ inherits
             ┌────────────┴────────────┐
             │                         │
┌────────────┴─────────────┐  ┌────────┴─────────────────┐
│      LLMClient           │  │   LocalLLMClient         │
│                          │  │                          │
│  Uses: AsyncOpenAI       │  │  Uses: aiohttp           │
│  For: API-based LLMs     │  │  For: Local LLM servers  │
│  - OpenRouter            │  │  - vLLM                  │
│  - OpenAI                │  │  - llama.cpp             │
│  - Any OpenAI-compatible │  │  - Any local server      │
│                          │  │                          │
│  Config:                 │  │  Config:                 │
│  - openrouter_api_key    │  │  - local_llm_base_url    │
│  - openrouter_base_url   │  │  - local_llm_model       │
│  - max_retries           │  │  - local_llm_max_tokens  │
│  - models_without_temp   │  │  - local_llm_max_retries │
│                          │  │                          │
│  call(prompt, model,     │  │  call(prompt, model,     │
│       temperature)       │  │       temperature)       │
│    -> str                │  │    -> str                │
└──────────────────────────┘  └──────────────────────────┘
```

## Usage in the Architecture

```
┌──────────────────────────────────────────────────────────┐
│                   ForecastingBot                         │
│                                                          │
│  Creates:                                                │
│  - MetaculusClient                                       │
│  - BaseLLMClient (LLMClient or LocalLLMClient)           │
│  - ResearchProvider                                      │
│  - Forecasters (Binary, Numeric, MultipleChoice)         │
└──────────────────────────────────────────────────────────┘
                          │
                          │ uses
                          ▼
┌──────────────────────────────────────────────────────────┐
│              BaseLLMClient (polymorphic)                 │
│                                                          │
│  Passed to:                                              │
│  ├─ LLMResearchProvider(llm_client: BaseLLMClient)       │
│  ├─ BinaryForecaster(llm_client: BaseLLMClient)          │
│  ├─ NumericForecaster(llm_client: BaseLLMClient)         │
│  └─ MultipleChoiceForecaster(llm_client: BaseLLMClient)  │
└──────────────────────────────────────────────────────────┘
                          │
                          │ can be
                          ▼
         ┌────────────────────────────────┐
         │  LLMClient  │  LocalLLMClient  │
         │  (runtime)  │  (runtime)       │
         └────────────────────────────────┘
```

## Configuration Flow

```
┌─────────────────────────────────────────────────────────┐
│                    config.py                            │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │ LLMConfig                                       │    │
│  │  - max_retries                                  │    │
│  │  - models_without_temperature                   │    │
│  │  - local_llm_model                              │    │
│  │  - local_llm_max_tokens                         │    │
│  │  - local_llm_temperature                        │    │
│  │  - local_llm_max_retries                        │    │
│  │  - local_llm_no_think                           │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │ APIConfig                                       │    │
│  │  - openrouter_api_key                           │    │
│  │  - openrouter_base_url                          │    │
│  │  - local_llm_base_url                           │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │ BotConfig                                       │    │
│  │  - default_model                                │    │ 
│  │  - default_temperature                          │    │
│  │  - concurrent_requests_limit                    │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                          │
                          │ used by
                          ▼
┌─────────────────────────────────────────────────────────┐
│                 LLM Clients                             │
│                                                         │
│  LLMClient reads:                                       │
│  - api_config.openrouter_*                              │
│  - llm_config.max_retries                               │
│  - llm_config.models_without_temperature                │
│  - bot_config.default_model                             │
│  - bot_config.default_temperature                       │
│                                                         │
│  LocalLLMClient reads:                                  │
│  - api_config.local_llm_base_url                        │
│  - llm_config.local_llm_*                               │
│  - bot_config.default_model (if not specified)          │
│  - bot_config.default_temperature (if not specified)    │
└─────────────────────────────────────────────────────────┘
```

## Call Signature Unification

Both clients implement the same interface:

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
        model: Model to use (defaults from config if None)
        temperature: Temperature (defaults from config if None)

    Returns:
        The LLM's response text
    """
```

## Example Usage Patterns

### Pattern 1: Direct Usage

```python
# API-based
client = LLMClient()
response = await client.call("What is 2+2?")

# Local
async with LocalLLMClient() as client:
    response = await client.call("What is 2+2?")
```

### Pattern 2: Polymorphic Usage (Recommended)

```python
def create_client(use_local: bool) -> BaseLLMClient:
    if use_local:
        return LocalLLMClient()
    else:
        return LLMClient()

# Works with either!
client = create_client(use_local=False)
response = await client.call("What is 2+2?")
```

### Pattern 3: Dependency Injection

```python
class Forecaster:
    def __init__(self, llm_client: BaseLLMClient):
        self.llm = llm_client

    async def forecast(self, question: str):
        return await self.llm.call(question)

# Can inject any client
forecaster = Forecaster(LLMClient())
# or
async with LocalLLMClient() as local:
    forecaster = Forecaster(local)
```

## Benefits of This Architecture

1. **Polymorphism**: Use `BaseLLMClient` type everywhere
2. **Flexibility**: Swap implementations at runtime
3. **Testability**: Easy to mock or create test implementations
4. **Extensibility**: Add new clients by extending `BaseLLMClient`
5. **Configuration**: All settings in one place
6. **Type Safety**: Abstract base class enforces interface
7. **DRY**: No duplicate code in consumers
8. **Maintainability**: Clear separation of concerns

## Adding a New LLM Client

To add a new LLM client (e.g., Anthropic direct API):

```python
class AnthropicClient(BaseLLMClient):
    def __init__(self, rate_limiter: Optional[RateLimiter] = None):
        super().__init__(rate_limiter)
        # Initialize Anthropic client

    async def call(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        # Implement Anthropic-specific logic
        pass
```

That's it! It will work with all existing forecasters and research providers.
