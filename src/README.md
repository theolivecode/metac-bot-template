# Refactored Forecasting Bot

This is a clean, modular refactoring of the original `main_with_no_framework.py` file.

## Architecture

The codebase follows clean architecture principles with clear separation of concerns:

```
src/
├── config.py              # Configuration and constants
├── api/                   # API clients
│   └── metaculus_client.py
├── research/              # Research providers
│   ├── base.py           # Abstract base class
│   ├── llm.py            # LLM-based research
│   ├── perplexity.py     # Perplexity API
│   └── asknews.py        # AskNews SDK
├── forecasting/           # Forecasting logic by question type
│   ├── binary.py
│   ├── numeric.py
│   └── multiple_choice.py
├── prompts/               # Prompt templates
│   ├── __init__.py
│   └── templates.py       # All prompt templates including multi-step research
├── utils/                 # Utilities
│   ├── llm_client.py     # LLM client wrapper
│   └── extractors.py     # Response parsing
└── main.py                # Main entry point
```

## Key Improvements

### 1. **Modular Design**
- Separated concerns into distinct modules
- Each module has a single, well-defined responsibility
- Easy to test and maintain

### 2. **Configuration Management**
- Centralized configuration in `config.py`
- Uses dataclasses for type safety
- Environment variables loaded once

### 3. **Type Safety**
- Type hints throughout the codebase
- Better IDE support and error detection

### 4. **Extensibility**
- Abstract base classes for research providers
- Easy to add new research sources
- Pluggable architecture

### 5. **Error Handling**
- Proper exception handling
- Informative error messages
- Graceful degradation

### 6. **Logging**
- Structured logging throughout
- Different log levels for different severity
- Easy to debug and monitor

### 7. **Code Reusability**
- DRY principle applied
- Shared utilities extracted
- No code duplication

## Research Pipeline

The LLMResearchProvider implements a comprehensive **5-step research pipeline** to provide high-quality research for forecasting:

### Step 1: Question Classification
- Analyzes the forecasting question to identify its primary field/domain
- Examples: politics, economics, technology, international relations, public health, sports, etc.
- Accepts optional field context from `question_details["field"]`
- Validates and refines provided field context with sub-field categorization

### Step 2: Entity Identification
- Identifies key entities relevant to the question based on field classification
- Searches for:
  - Countries and regions
  - Political leaders and government officials
  - Organizations and institutions
  - Companies and corporations
  - International bodies and agreements
  - Key individuals

### Step 3: Entity Analysis
- Analyzes characteristics and relationships of identified entities
- Examines for each entity:
  - Personality/character (for individuals) or institutional approach (for organizations)
  - Typical approach to similar situations or tasks
  - Relationships with other identified entities
  - Current motivations and incentives
  - Historical patterns of behavior

### Step 4: News Search
- Searches for 10-20 recent, high-quality news articles
- Prioritizes:
  - Recent news (within last few weeks/months)
  - Authoritative sources
  - Information relevant to resolution criteria
  - Quantitative data and expert analysis
- Covers:
  - Specific question developments
  - Entity-related news
  - Field-specific trends
  - Expert opinions and forecasts

### Step 5: Final Report Generation
- Synthesizes all research into a comprehensive report
- Includes:
  - Current state of affairs summary
  - Key entities and their likely behaviors
  - Recent trends and developments
  - Important dates, deadlines, or milestones
  - Expert opinions and market expectations
  - Uncertainties and information gaps
- Optimized as input for the Forecaster

### Benefits of Multi-Step Research
- **Structured**: Systematic approach ensures comprehensive coverage
- **Transparent**: Each step logs progress for visibility
- **Contextual**: Provides deep understanding of entities and relationships
- **Current**: Focuses on recent, relevant news and developments
- **Actionable**: Report format optimized for forecasting decisions

## Usage

### Basic Usage

```python
# Run from the project root
python -m src.main
```

### Configuration

Edit `src/config.py` or set environment variables:

```bash
# Required
export METACULUS_TOKEN="your_token"
export OPENROUTER_API_KEY="your_key"
export OPENROUTER_BASE_URL="https://openrouter.ai/api/v1"

# Optional (for different research providers)
export PERPLEXITY_API_KEY="your_key"
export ASKNEWS_CLIENT_ID="your_id"
export ASKNEWS_SECRET="your_secret"
```

### Programmatic Usage

```python
from src import ForecastingBot
from src.config import bot_config

# Configure
bot_config.submit_prediction = False
bot_config.num_runs_per_question = 3

# Run
bot = ForecastingBot()
await bot.forecast_questions([(question_id, post_id)])
```

## Adding New Features

### Adding New LLM Client

1. In `src/utils/llm_client.py`, Inferite from `LLMBaseClient`
2. Implement `call()` method
3. Register in `src/research/__init__.py`

```python
class CustomLLMClient(BaseLLMClient):
    def __init__():
        # ...

    async def call(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        # ...
        return answer
```

The `LLMClient` is using `AsyncOpenAI()` as a client, with `OpenRouter` as default:
```python
self.client = AsyncOpenAI(
    base_url=self.base_url,
    api_key=self.api_key,
    max_retries=llm_config.max_retries,
)
```
We can use the `call(prompt=prompt, model=model, temperatrue=temperature)` to call different models using the `AsyncOpenAI` client. 


### Adding a New Research Provider

1. Create a new file in `src/research/`
2. Inherit from `ResearchProvider`
3. Implement `conduct_research()` method
4. Register in `src/research/__init__.py`

Example:
```python
from .base import ResearchProvider

class CustomResearchProvider(ResearchProvider):
    async def conduct_research(self, question, question_details=None):
        # New strategy to research
        return research_results
```

The `LLMResearchProvider` demonstrates a sophisticated multi-step approach:
- Uses dedicated prompt templates for each research step
- Orchestrates multiple LLM calls to build comprehensive research
- Each step builds on previous results (classification → entities → analysis → news → report)
- See the Research Pipeline section above for full details

You can implement simpler single-step research providers (like `PerplexityResearchProvider`) or complex multi-step pipelines depending on your needs.

### Use Different Forecasting Methods

Implement the Forecasters in the `src/forecasting/*.py`. 

Example:
```python
async def _get_single_forecast(self, content: str) -> Tuple[float, str]:
    # New strategy to forecast
    return probability, comment
```

### Adding a New Question Type

1. Create a new forecaster in `src/forecasting/`
2. Follow the pattern of existing forecasters
3. Add to the main orchestration in `src/main.py`

## Testing

```bash
# Set test mode
export USE_EXAMPLE_QUESTIONS=True
export SUBMIT_PREDICTION=False

# Run
python -m src.main
```

## Benefits Over Original Code

1. **Maintainability**: Easy to find and modify specific functionality
2. **Testability**: Each module can be tested independently
3. **Readability**: Clear structure and naming conventions
4. **Scalability**: Easy to add new features without modifying existing code
5. **Debugging**: Better logging and error messages
6. **Collaboration**: Multiple developers can work on different modules
7. **Enhanced Research**: Multi-step research pipeline provides comprehensive, structured analysis for better forecasting accuracy
