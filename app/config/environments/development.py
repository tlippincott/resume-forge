"""
Development environment configuration overrides.

To use: Set ENV=development in your .env file or environment variables.

Development settings prioritize:
- Faster timeouts for quick iteration
- More verbose logging for debugging
- Lower retry delays
"""

# LLM Configuration Overrides
LLM_CONFIG_OVERRIDES = {
    "scoring_timeout": 60,      # Faster in dev (vs 90s in prod)
    "rewriting_timeout": 90,    # Faster in dev (vs 120s in prod)
    "analysis_timeout": 45,     # Faster in dev (vs 60s in prod)
}

# Logging Configuration Overrides
LOGGING_CONFIG_OVERRIDES = {
    "log_level": "DEBUG",       # More verbose in dev
    "console_level": "DEBUG",   # Show debug in console
    "file_level": "DEBUG"       # Full debug logs to file
}

# API Configuration Overrides
API_CONFIG_OVERRIDES = {
    "default_timeout": 45,      # Shorter timeouts in dev
    "initial_retry_delay": 1,   # Faster retries in dev
}

# Business Rules (no changes from defaults)
BUSINESS_CONFIG_OVERRIDES = {}

# Scoring (no changes from defaults)
SCORING_CONFIG_OVERRIDES = {}
