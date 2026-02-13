"""
Main configuration settings combining all config models.

This module loads configuration from:
1. .env file (if present)
2. Environment variables
3. Default values in models

Environment variables are automatically parsed by Pydantic.
"""

import os
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from app.config.models import (
    APIConfig,
    LLMConfig,
    BusinessRulesConfig,
    ScoringConfig,
    LoggingConfig
)


# Load .env file if it exists (project root)
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)


class Config(BaseModel):
    """
    Main configuration class combining all configuration sections.

    Usage:
        from app.config import config

        # Access configuration
        timeout = config.api.default_timeout
        temp = config.llm.temperature_creative
        min_bullets = config.business.bullet_selection_min
    """
    api: APIConfig
    llm: LLMConfig
    business: BusinessRulesConfig
    scoring: ScoringConfig
    logging: LoggingConfig

    @classmethod
    def load(cls) -> "Config":
        """
        Load configuration from environment variables and .env file.

        Returns:
            Config instance with all sections populated
        """
        # Load each section from environment
        api = APIConfig(
            api_key=os.getenv("API_KEY", ""),
            model_name=os.getenv("MODEL_NAME", "gpt-4o-mini"),
            base_url=os.getenv("API_BASE_URL"),
            default_timeout=int(os.getenv("DEFAULT_TIMEOUT", "60")),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            initial_retry_delay=int(os.getenv("INITIAL_RETRY_DELAY", "2")),
            max_retry_delay=int(os.getenv("MAX_RETRY_DELAY", "32"))
        )

        llm = LLMConfig(
            temperature_deterministic=float(os.getenv("LLM_TEMPERATURE_DETERMINISTIC", "0.0")),
            temperature_creative=float(os.getenv("LLM_TEMPERATURE_CREATIVE", "0.7")),
            scoring_timeout=int(os.getenv("LLM_SCORING_TIMEOUT", "90")),
            rewriting_timeout=int(os.getenv("LLM_REWRITING_TIMEOUT", "120")),
            analysis_timeout=int(os.getenv("LLM_ANALYSIS_TIMEOUT", "60")),
            cover_letter_timeout=int(os.getenv("LLM_COVER_LETTER_TIMEOUT", "90"))
        )

        business = BusinessRulesConfig(
            bullet_selection_min=int(os.getenv("BUSINESS_BULLET_SELECTION_MIN", "38")),
            bullet_selection_max=int(os.getenv("BUSINESS_BULLET_SELECTION_MAX", "42")),
            spins_min=int(os.getenv("BUSINESS_SPINS_MIN", "10")),
            spins_max=int(os.getenv("BUSINESS_SPINS_MAX", "12")),
            programmer_min=int(os.getenv("BUSINESS_PROGRAMMER_MIN", "10")),
            programmer_max=int(os.getenv("BUSINESS_PROGRAMMER_MAX", "12")),
            analyst_min=int(os.getenv("BUSINESS_ANALYST_MIN", "0")),
            analyst_max=None if os.getenv("BUSINESS_ANALYST_MAX") is None else int(os.getenv("BUSINESS_ANALYST_MAX"))
        )

        scoring = ScoringConfig(
            required_skill_weight=int(os.getenv("SCORING_REQUIRED_SKILL_WEIGHT", "3")),
            preferred_skill_weight=int(os.getenv("SCORING_PREFERRED_SKILL_WEIGHT", "1")),
            impact_bonus=int(os.getenv("SCORING_IMPACT_BONUS", "2")),
            category_similarity_weight=int(os.getenv("SCORING_CATEGORY_SIMILARITY_WEIGHT", "2")),
            skill_overlap_weight=int(os.getenv("SCORING_SKILL_OVERLAP_WEIGHT", "1")),
            skill_coverage_penalty=float(os.getenv("SCORING_SKILL_COVERAGE_PENALTY", "0.5"))
        )

        logging = LoggingConfig(
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_dir=os.getenv("LOG_DIR", "logs"),
            log_filename=os.getenv("LOG_FILENAME", "resume_forge.log"),
            console_level=os.getenv("LOG_CONSOLE_LEVEL", "INFO"),
            file_level=os.getenv("LOG_FILE_LEVEL", "DEBUG")
        )

        return cls(
            api=api,
            llm=llm,
            business=business,
            scoring=scoring,
            logging=logging
        )


# Global config instance - load once at import time
config = Config.load()
