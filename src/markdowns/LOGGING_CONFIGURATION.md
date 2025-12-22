# Logging Configuration Guide

The forecasting bot now has centralized, configurable logging.

## Configuration Location

All logging settings are in **`src/config.py`** in the `LoggingConfig` dataclass:

```python
@dataclass
class LoggingConfig:
    """Logging configuration."""

    # Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Whether to log to file
    log_to_file: bool = False
    log_file_path: str = "forecasting_bot.log"
```

## How to Change Logging Level

### Method 1: Environment Variable (Recommended)

Set the `LOG_LEVEL` environment variable:

```bash
# In your shell
export LOG_LEVEL=DEBUG

# Or in .env file
echo "LOG_LEVEL=DEBUG" >> .env

# Then run the bot
python -m src.main
```

**Available levels:**
- `DEBUG` - Most verbose, shows all debug messages
- `INFO` - Default, shows informational messages
- `WARNING` - Shows warnings and errors only
- `ERROR` - Shows errors only
- `CRITICAL` - Shows only critical errors

### Method 2: Edit config.py Directly

Edit `src/config.py`:

```python
@dataclass
class LoggingConfig:
    log_level: str = os.getenv("LOG_LEVEL", "DEBUG")  # Changed from "INFO" to "DEBUG"
    # ...
```

### Method 3: Programmatic (for testing)

```python
from src.config import logging_config

# Change before importing main
logging_config.log_level = "DEBUG"

# Then run your code
```

## Enable File Logging

To save logs to a file in addition to console output:

### In config.py:

```python
@dataclass
class LoggingConfig:
    log_to_file: bool = True  # Enable file logging
    log_file_path: str = "forecasting_bot.log"  # Where to save logs
```

### Or programmatically:

```python
from src.config import logging_config

logging_config.log_to_file = True
logging_config.log_file_path = "my_custom_log.log"
```

## Log Format

The default format is:
```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

Which produces logs like:
```
2025-12-13 10:30:45,123 - src.main - INFO - Starting forecast
2025-12-13 10:30:46,456 - src.utils.llm_client - DEBUG - Calling API LLM with model=...
```

### Custom Log Format

Edit `src/config.py`:

```python
@dataclass
class LoggingConfig:
    log_format: str = "%(levelname)s - %(message)s"  # Simple format
    # Or
    log_format: str = "[%(asctime)s] %(name)s:%(lineno)d - %(levelname)s - %(message)s"  # Detailed
```

## Examples

### Example 1: Debug Mode for Development

```bash
# In .env or shell
export LOG_LEVEL=DEBUG

python -m src.main
```

Output will include detailed debug messages:
```
2025-12-13 10:30:45 - src.utils.llm_client - DEBUG - Calling API LLM with model=anthropic/claude-sonnet-4.5, temperature=0.3
2025-12-13 10:30:45 - src.utils.llm_client - DEBUG - LLM response received (length: 1234 chars)
2025-12-13 10:30:46 - src.research.llm - DEBUG - Extracted Probability: 0.75
```

### Example 2: Production Mode (Quiet)

```bash
export LOG_LEVEL=WARNING

python -m src.main
```

Only warnings and errors will be shown.

### Example 3: Save Debug Logs to File

Edit `src/config.py`:
```python
@dataclass
class LoggingConfig:
    log_level: str = os.getenv("LOG_LEVEL", "DEBUG")
    log_to_file: bool = True
    log_file_path: str = "debug.log"
```

Now logs will go to both console AND `debug.log` file.

### Example 4: Different Levels for Different Environments

```bash
# Development
export LOG_LEVEL=DEBUG
python -m src.main

# Production
export LOG_LEVEL=INFO
python -m src.main

# CI/CD
export LOG_LEVEL=WARNING
python -m src.main
```

## Logging in Your Code

If you're adding new modules, use this pattern:

```python
import logging

logger = logging.getLogger(__name__)

class MyClass:
    def my_method(self):
        logger.debug("Debug message - detailed info")
        logger.info("Info message - general info")
        logger.warning("Warning message - something unexpected")
        logger.error("Error message - something failed")
        logger.critical("Critical message - severe error")
```

**Don't add `logging.basicConfig()`** - it's already configured in `main.py`.

## Architecture

Logging is configured **once** at the application entry point (`src/main.py`):

```
src/main.py
├─ Reads logging_config from src/config.py
├─ Configures logging with handlers
│  ├─ Console handler (always)
│  └─ File handler (if enabled)
└─ All other modules use logger = logging.getLogger(__name__)
```

This ensures:
- ✅ Single source of truth for logging config
- ✅ No duplicate logging configuration
- ✅ Consistent logging across all modules
- ✅ Easy to change settings globally

## Troubleshooting

### Logs not showing up?

1. Check your log level:
   ```python
   from src.config import logging_config
   print(f"Current log level: {logging_config.log_level}")
   ```

2. Make sure you're using the logger correctly:
   ```python
   logger = logging.getLogger(__name__)  # ✅ Correct
   # NOT:
   # logging.debug("...")  # ❌ Wrong - bypasses configuration
   ```

### Too many logs?

Increase the log level:
```bash
export LOG_LEVEL=WARNING  # Only show warnings and errors
```

### Want module-specific logging?

You can set different levels for different modules:

```python
# In main.py or your script
import logging

# Set root level
logging.getLogger().setLevel(logging.INFO)

# But set specific modules to DEBUG
logging.getLogger('src.utils.llm_client').setLevel(logging.DEBUG)
logging.getLogger('src.research').setLevel(logging.DEBUG)
```

## Summary

| Setting | Location | How to Change |
|---------|----------|---------------|
| Log Level | `src/config.py` | Set `LOG_LEVEL` env var or edit config |
| Log Format | `src/config.py` | Edit `log_format` in `LoggingConfig` |
| File Logging | `src/config.py` | Set `log_to_file = True` |
| File Path | `src/config.py` | Set `log_file_path` |

**Quick Start:**
```bash
# Debug mode
export LOG_LEVEL=DEBUG
python -m src.main

# Production mode
export LOG_LEVEL=INFO
python -m src.main
```
