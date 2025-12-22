# Logging Configuration Refactoring Summary

## Overview

Centralized and made logging configuration adjustable through `src/config.py` instead of having hardcoded logging setup scattered across multiple modules.

## Changes Made

### 1. Added LoggingConfig to config.py

**File:** `src/config.py`

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

# Global instance
logging_config = LoggingConfig()
```

**Features:**
- ✅ Log level configurable via `LOG_LEVEL` environment variable
- ✅ Custom log format support
- ✅ Optional file logging
- ✅ Centralized configuration

### 2. Removed Duplicate Logging Configuration

Removed `logging.basicConfig()` calls from individual modules:

- ❌ **src/utils/llm_client.py** - Removed duplicate config
- ❌ **src/research/llm.py** - Removed duplicate config
- ❌ **src/forecasting/binary.py** - Removed duplicate config

**Before (each module):**
```python
# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Hardcoded!
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
```

**After (each module):**
```python
logger = logging.getLogger(__name__)  # That's it!
```

### 3. Centralized Logging Setup in main.py

**File:** `src/main.py`

```python
from .config import logging_config

# Configure logging based on config
log_level = getattr(logging, logging_config.log_level.upper(), logging.INFO)
handlers = []

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(logging_config.log_format))
handlers.append(console_handler)

# Optional file handler
if logging_config.log_to_file:
    file_handler = logging.FileHandler(logging_config.log_file_path)
    file_handler.setFormatter(logging.Formatter(logging_config.log_format))
    handlers.append(file_handler)

logging.basicConfig(
    level=log_level,
    format=logging_config.log_format,
    handlers=handlers,
)
logger = logging.getLogger(__name__)
```

**Benefits:**
- ✅ Single configuration point
- ✅ Respects environment variables
- ✅ Supports both console and file output
- ✅ Consistent across all modules

## How to Use

### Change Log Level

**Via Environment Variable (Recommended):**
```bash
export LOG_LEVEL=DEBUG
python -m src.main
```

**Via .env file:**
```bash
echo "LOG_LEVEL=DEBUG" >> .env
python -m src.main
```

**Directly in config.py:**
```python
@dataclass
class LoggingConfig:
    log_level: str = "DEBUG"  # Changed from INFO to DEBUG
```

### Available Log Levels

- `DEBUG` - Most verbose, all debug messages
- `INFO` - Default, informational messages
- `WARNING` - Warnings and errors only
- `ERROR` - Errors only
- `CRITICAL` - Critical errors only

### Enable File Logging

Edit `src/config.py`:
```python
@dataclass
class LoggingConfig:
    log_to_file: bool = True
    log_file_path: str = "forecasting_bot.log"
```

Now logs will be saved to `forecasting_bot.log` in addition to console output.

## Architecture

```
┌─────────────────────────────────────────────┐
│           src/config.py                     │
│                                             │
│  LoggingConfig                              │
│  - log_level (from env or default)          │
│  - log_format                               │
│  - log_to_file                              │
│  - log_file_path                            │
│                                             │
│  logging_config = LoggingConfig()           │
└─────────────────────────────────────────────┘
                    │
                    │ imported by
                    ▼
┌─────────────────────────────────────────────┐
│           src/main.py                       │
│                                             │
│  1. Reads logging_config                    │
│  2. Configures logging.basicConfig()        │
│  3. Sets up handlers (console + file)       │
│                                             │
│  ⚙️ Logging configured ONCE here            │
└─────────────────────────────────────────────┘
                    │
                    │ used by all modules
                    ▼
┌─────────────────────────────────────────────┐
│  All other modules just use:                │
│                                             │
│  logger = logging.getLogger(__name__)       │
│                                             │
│  - src/utils/llm_client.py                  │
│  - src/research/llm.py                      │
│  - src/forecasting/binary.py                │
│  - src/forecasting/numeric.py               │
│  - src/forecasting/multiple_choice.py       │
│  - ... etc                                  │
└─────────────────────────────────────────────┘
```

## Files Changed

1. ✅ **src/config.py** - Added `LoggingConfig` dataclass
2. ✅ **src/main.py** - Centralized logging configuration
3. ✅ **src/utils/llm_client.py** - Removed duplicate config
4. ✅ **src/research/llm.py** - Removed duplicate config
5. ✅ **src/forecasting/binary.py** - Removed duplicate config

## Documentation Created

1. ✅ **LOGGING_CONFIGURATION.md** - Complete user guide
2. ✅ **LOGGING_REFACTORING_SUMMARY.md** - This file

## Benefits

### Before Refactoring ❌

- ❌ Logging config scattered across multiple files
- ❌ Hardcoded log levels (DEBUG, INFO, etc.)
- ❌ Inconsistent between modules
- ❌ Hard to change globally
- ❌ No environment variable support
- ❌ No file logging option

### After Refactoring ✅

- ✅ Single source of truth in `config.py`
- ✅ Configurable via environment variables
- ✅ Consistent across all modules
- ✅ Easy to change globally
- ✅ Supports file logging
- ✅ Production-ready configuration

## Testing

All modules compile successfully:

```bash
python -m py_compile src/config.py \
    src/main.py \
    src/utils/llm_client.py \
    src/research/llm.py \
    src/forecasting/binary.py

✅ All modules compile successfully!
```

## Examples

### Development (Verbose Logging)
```bash
export LOG_LEVEL=DEBUG
python -m src.main
```

### Production (Quiet Logging)
```bash
export LOG_LEVEL=WARNING
python -m src.main
```

### Save Logs to File
```python
# In config.py
@dataclass
class LoggingConfig:
    log_to_file: bool = True
    log_file_path: str = "production.log"
```

## Migration Guide

### For Developers Adding New Modules

**Old Way (Don't do this):**
```python
import logging

logging.basicConfig(level=logging.DEBUG)  # ❌ Don't configure here
logger = logging.getLogger(__name__)
```

**New Way (Correct):**
```python
import logging

logger = logging.getLogger(__name__)  # ✅ Just get the logger
```

The logging is already configured in `main.py`, so you only need to get a logger instance.

## Quick Reference

| Task | Command |
|------|---------|
| Set log level to DEBUG | `export LOG_LEVEL=DEBUG` |
| Set log level to INFO | `export LOG_LEVEL=INFO` |
| Set log level to WARNING | `export LOG_LEVEL=WARNING` |
| Enable file logging | Edit `log_to_file = True` in config.py |
| Change log file location | Edit `log_file_path` in config.py |
| Customize log format | Edit `log_format` in config.py |

## See Also

- **LOGGING_CONFIGURATION.md** - Detailed configuration guide
- **src/config.py** - Configuration source code
- **src/main.py** - Logging initialization code
