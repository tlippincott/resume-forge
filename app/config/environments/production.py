"""
Production environment configuration overrides.

To use: Set ENV=production in your .env file or environment variables.

Production settings prioritize:
- More conservative timeouts for reliability
- Less verbose logging for performance
- Longer retry delays to avoid rate limiting
"""

# LLM Configuration Overrides
LLM_CONFIG_OVERRIDES = {
    "scoring_timeout": 120,         # More conservative in prod
    "rewriting_timeout": 150,       # Allow more time in prod
    "analysis_timeout": 90,         # More time for analysis
    "cover_letter_timeout": 120,    # More time for cover letters
}

# Logging Configuration Overrides
LOGGING_CONFIG_OVERRIDES = {
    "log_level": "WARNING",     # Less verbose in prod
    "console_level": "INFO",    # Only important messages
    "file_level": "INFO"        # Less detailed file logs
}

# API Configuration Overrides
API_CONFIG_OVERRIDES = {
    "default_timeout": 90,      # Longer timeouts in prod
    "max_retries": 5,           # More retries in prod
    "initial_retry_delay": 3,   # Longer delays to avoid rate limits
    "max_retry_delay": 60,      # Higher max delay
}

# Business Rules (no changes from defaults)
BUSINESS_CONFIG_OVERRIDES = {}

# Scoring (no changes from defaults)
SCORING_CONFIG_OVERRIDES = {}
