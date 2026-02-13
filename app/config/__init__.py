"""
Configuration module for Resume Forge.

This module provides centralized configuration management using Pydantic.
All configuration is loaded from environment variables and .env files.

Usage:
    from app.config import config

    # Access configuration values
    timeout = config.api.default_timeout
    temperature = config.llm.temperature_creative
    min_bullets = config.business.bullet_selection_min
    required_weight = config.scoring.required_skill_weight
    log_level = config.logging.log_level

Configuration Sections:
- api: OpenAI API configuration (keys, timeouts, retries)
- llm: LLM parameters (temperatures, operation-specific timeouts)
- business: Business rules (bullet selection, section sizes)
- scoring: Intelligence scoring weights
- logging: Logging configuration

Environment Variables:
See models.py for complete list of environment variables and their defaults.
"""

from app.config.settings import config

__all__ = ["config"]
