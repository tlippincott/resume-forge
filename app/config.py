"""
DEPRECATED: Legacy configuration module.

This module is maintained for backward compatibility only.
New code should use: from app.config import config

Migration:
- config.API_KEY -> config.api.api_key
- config.MODEL_NAME -> config.api.model_name
"""

from app.config import config

# Backward compatibility exports
API_KEY = config.api.api_key
MODEL_NAME = config.api.model_name

# Validate API key
if not API_KEY:
    raise ValueError("API_KEY not found in environment. Please check your .env file.")
