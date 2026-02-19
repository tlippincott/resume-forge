"""
Pydantic configuration models for Resume Forge.

All configuration values are defined here with validation, defaults, and documentation.

Why Pydantic:
- Built-in .env file loading
- Automatic type validation
- Environment variable parsing
- Clear error messages
- Field validators for complex rules
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional


class APIConfig(BaseModel):
    """
    OpenAI API configuration.

    Env vars:
        API_KEY: OpenAI API key (required)
        MODEL_NAME: Model to use (default: gpt-4o-mini)
        API_BASE_URL: Custom API base URL (optional)
        DEFAULT_TIMEOUT: Default timeout in seconds (default: 60)
        MAX_RETRIES: Maximum retry attempts (default: 3)
        INITIAL_RETRY_DELAY: Initial retry delay in seconds (default: 2)
        MAX_RETRY_DELAY: Maximum retry delay in seconds (default: 32)
    """
    api_key: str = Field(..., description="OpenAI API key")
    model_name: str = Field(default="gpt-4o-mini", description="Model to use for LLM calls")
    base_url: Optional[str] = Field(default=None, description="Custom API base URL")
    default_timeout: int = Field(default=60, ge=1, le=300, description="Default timeout in seconds")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    initial_retry_delay: int = Field(default=2, ge=1, le=10, description="Initial retry delay in seconds")
    max_retry_delay: int = Field(default=32, ge=1, le=120, description="Maximum retry delay in seconds")

    class Config:
        env_prefix = ""  # No prefix, use exact env var names


class LLMConfig(BaseModel):
    """
    LLM-specific parameters (temperature, timeouts per operation).

    These control LLM behavior for different types of operations.
    """
    temperature_deterministic: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Temperature for deterministic operations (scoring, analysis)"
    )
    temperature_creative: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Temperature for creative operations (rewriting, cover letters)"
    )
    scoring_timeout: int = Field(
        default=90,
        ge=1,
        le=300,
        description="Timeout for bullet scoring operations"
    )
    rewriting_timeout: int = Field(
        default=120,
        ge=1,
        le=300,
        description="Timeout for bullet rewriting operations"
    )
    analysis_timeout: int = Field(
        default=60,
        ge=1,
        le=300,
        description="Timeout for intelligence analysis operations"
    )
    cover_letter_timeout: int = Field(
        default=90,
        ge=1,
        le=300,
        description="Timeout for cover letter generation"
    )

    class Config:
        env_prefix = "LLM_"


class BusinessRulesConfig(BaseModel):
    """
    Business logic rules for resume generation.

    These control the core resume generation logic:
    - How many bullets to select
    - Section size constraints
    """
    spins_count: int = Field(default=12, ge=1, description="Exact SPINS bullets per resume")
    programmer_count: int = Field(default=12, ge=1, description="Exact Programmer bullets per resume")
    analyst_count: int = Field(default=10, ge=1, description="Exact Analyst bullets per resume")

    class Config:
        env_prefix = "BUSINESS_"


class ScoringConfig(BaseModel):
    """
    Scoring weights for intelligent bullet ranking.

    These weights control how bullets are scored against job descriptions.
    """
    required_skill_weight: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Weight for required skill matches"
    )
    preferred_skill_weight: int = Field(
        default=1,
        ge=0,
        le=10,
        description="Weight for preferred skill matches"
    )
    impact_bonus: int = Field(
        default=2,
        ge=0,
        le=10,
        description="Bonus for bullets with quantified impact"
    )
    category_similarity_weight: int = Field(
        default=2,
        ge=0,
        le=10,
        description="Weight for category similarity in replacement suggestions"
    )
    skill_overlap_weight: int = Field(
        default=1,
        ge=0,
        le=10,
        description="Weight for skill overlap in replacement suggestions"
    )
    skill_coverage_penalty: float = Field(
        default=0.5,
        ge=0.0,
        le=10.0,
        description="Penalty per duplicated skill in replacement suggestions"
    )

    class Config:
        env_prefix = "SCORING_"


class LoggingConfig(BaseModel):
    """
    Logging configuration.

    Controls logging levels, output destinations, and formats.
    """
    log_level: str = Field(
        default="INFO",
        description="Root log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    log_dir: str = Field(default="logs", description="Log directory path")
    log_filename: str = Field(default="resume_forge.log", description="Log file name")
    console_level: str = Field(
        default="INFO",
        description="Console handler log level"
    )
    file_level: str = Field(
        default="DEBUG",
        description="File handler log level"
    )

    @field_validator("log_level", "console_level", "file_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Ensure log level is valid."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()

    class Config:
        env_prefix = "LOG_"


class OutputConfig(BaseModel):
    """Output file naming configuration."""
    resume_pdf_name: str = Field(
        default="resume",
        description="Resume PDF filename (without .pdf extension)"
    )
    cover_letter_pdf_name: str = Field(
        default="cover_letter",
        description="Cover letter PDF filename (without .pdf extension)"
    )
