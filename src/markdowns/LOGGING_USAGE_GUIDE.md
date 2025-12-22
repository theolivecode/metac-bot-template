# How to Use Logging with LLM Clients

## The Problem (Fixed!)

Previously, when using `LocalLLMClient` or `LLMClient` outside of `main.py`, logging wasn't configured, so you wouldn't see any log messages.

**This is now fixed!** ✅

## The Solution: `setup_logging()`

We've added a `setup_logging()` function that can be called from anywhere to initialize logging.

### Usage

#### Option 1: Quick Setup (Recommended)

```python
from src.config import setup_logging
from src.utils import LocalLLMClient

# Setup logging first
setup_logging(level="DEBUG")  # or "INFO", "WARNING", etc.

# Now use the client - logs will appear!
async with LocalLLMClient() as client:
    response = await client.call("What is 2+2?")
    print(response)
```

#### Option 2: Use Default Config

```python
from src.config import setup_logging
from src.utils import LLMClient

# Setup logging with defaults from config.py
setup_logging()

# Use the client
client = LLMClient()
response = await client.call("What is 2+2?")
```

#### Option 3: Customize Everything

```python
from src.config import setup_logging
from src.utils import LocalLLMClient

# Setup with custom settings
setup_logging(
    level="DEBUG",      # Log level
    log_to_file=True    # Also save to file
)

# Now logs will appear in console AND file
async with LocalLLMClient() as client:
    response = await client.call("What is 2+2?")
```

## Examples

### Example 1: Using LocalLLMClient with Logging

```python
import asyncio
from src.config import setup_logging
from src.utils import LocalLLMClient

async def main():
    # IMPORTANT: Setup logging first!
    setup_logging(level="DEBUG")

    # Now you'll see all the logs
    async with LocalLLMClient() as client:
        response = await client.call("Explain quantum computing")
        print(f"Response: {response}")

if __name__ == "__main__":
    asyncio.run(main())
```

**Output will include:**
```
2025-12-13 10:30:45 - src.config - INFO - Logging configured: level=DEBUG, log_to_file=False
2025-12-13 10:30:46 - src.utils.llm_client - INFO - Calling Local LLM with model=Qwen/Qwen3-32B (No Think), temperature=0.2
2025-12-13 10:30:47 - src.utils.llm_client - INFO - Token usage: {'prompt_tokens': 10, 'completion_tokens': 50}
2025-12-13 10:30:47 - src.utils.llm_client - DEBUG - Local LLM response received (length: 234 chars)
Response: [Your response here]
```

### Example 2: Using LLMClient with Logging

```python
import asyncio
from src.config import setup_logging
from src.utils import LLMClient

async def main():
    setup_logging(level="INFO")  # Less verbose

    client = LLMClient()
    response = await client.call("What is the capital of France?")
    print(f"Response: {response}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Example 3: Running the Example File

The `llm_client_example.py` now automatically sets up logging:

```bash
# Just run it - logging is already configured
python -m src.utils.llm_client_example
```

You'll see debug logs like:
```
2025-12-13 10:30:45 - src.config - INFO - Logging configured: level=DEBUG, log_to_file=False
2025-12-13 10:30:46 - src.utils.llm_client - DEBUG - Calling API LLM with model=anthropic/claude-sonnet-4.5, temperature=0.3
...
```

## When to Call setup_logging()

### ✅ DO call setup_logging():

1. **At the start of standalone scripts:**
   ```python
   from src.config import setup_logging
   setup_logging()
   # ... rest of your code
   ```

2. **In example files:**
   ```python
   # At the top of the file
   setup_logging(level="DEBUG")
   ```

3. **In tests:**
   ```python
   def test_llm_client():
       setup_logging(level="DEBUG")
       # ... your test
   ```

4. **In Jupyter notebooks:**
   ```python
   from src.config import setup_logging
   setup_logging(level="INFO")
   ```

### ❌ DON'T call setup_logging():

1. **In library modules** (utils, forecasting, research, etc.)
   - Just use `logger = logging.getLogger(__name__)`
   - Don't configure logging in library code

2. **When importing from main.py**
   - `main.py` already calls `setup_logging()`
   - No need to call it again

## Function Reference

```python
def setup_logging(level: Optional[str] = None, log_to_file: Optional[bool] = None):
    """
    Setup logging configuration.

    Args:
        level: Log level override (DEBUG, INFO, WARNING, ERROR, CRITICAL)
               If None, uses logging_config.log_level from config.py
        log_to_file: Whether to log to file (overrides config)
                     If None, uses logging_config.log_to_file from config.py
    """
```

### Parameters

- **level** (optional): `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`, `"CRITICAL"`
  - Default: Uses `logging_config.log_level` from config.py (usually `"INFO"`)
  - Set to `"DEBUG"` for verbose logging
  - Set to `"WARNING"` for quiet logging

- **log_to_file** (optional): `True` or `False`
  - Default: Uses `logging_config.log_to_file` from config.py (usually `False`)
  - Set to `True` to also save logs to `forecasting_bot.log`

## Troubleshooting

### Still not seeing logs?

1. **Make sure you called setup_logging():**
   ```python
   from src.config import setup_logging
   setup_logging(level="DEBUG")  # Add this!
   ```

2. **Check the log level:**
   ```python
   # If set to WARNING, you won't see INFO or DEBUG messages
   setup_logging(level="DEBUG")  # Use DEBUG to see everything
   ```

3. **Verify it's being called before the client:**
   ```python
   # ✅ Correct order
   setup_logging()
   client = LocalLLMClient()

   # ❌ Wrong order
   client = LocalLLMClient()
   setup_logging()  # Too late!
   ```

### Logs appearing twice?

If you see duplicate log messages, you might be calling `setup_logging()` multiple times.

**Solution:** Only call it once at the start of your script.

## Summary

| Scenario | What to do |
|----------|------------|
| Using `LocalLLMClient` standalone | Call `setup_logging()` first |
| Using `LLMClient` standalone | Call `setup_logging()` first |
| Running `main.py` | Nothing - already configured |
| Running examples | Already configured in example files |
| Writing tests | Call `setup_logging()` in test setup |
| Writing library code | Just use `logger = logging.getLogger(__name__)` |

**Quick template for standalone scripts:**

```python
from src.config import setup_logging
from src.utils import LocalLLMClient

# Always start with this
setup_logging(level="DEBUG")

# Now use your clients
async with LocalLLMClient() as client:
    response = await client.call("Your prompt")
```
