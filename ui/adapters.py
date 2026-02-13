"""
UI Adapters: App Layer → UI Layer Boundary Translation

This module provides adapter functions that translate app layer exceptions
to UI-friendly Result types. These adapters form the boundary between business
logic and presentation logic.

Architecture:
- App layer raises typed exceptions (FileOperationError, ValidationError, etc.)
- Adapters catch exceptions and convert to Success[T] or Failure
- UI handlers receive Result types and format for Gradio components
- No try/except blocks in UI handlers - all error handling here
"""

from typing import Any, Dict
from app.resume_engine import generate_resume
from app.cover_engine import generate_cover_letter
from app.exceptions import (
    ResumeForgeError,
    ValidationError,
    FileOperationError,
    DataProcessingError,
    LLMServiceError
)
from app.error_result import Result, success, failure
from app.logging_config import get_logger

logger = get_logger(__name__)


def generate_resume_adapter(
    job_description: str,
    company_name: str,
    company_info: str,
    bullet_file: str,
    job_change: bool
) -> Result[Dict[str, Any]]:
    """
    Adapter for generate_resume() - translates exceptions to Result types.

    Args:
        job_description: Target job description
        company_name: Target company name
        company_info: Information about the target company
        bullet_file: Path to bullet library JSON file
        job_change: Boolean indicating if this is a career change

    Returns:
        Success[dict] containing resume data, or Failure with error message
    """
    try:
        logger.debug(f"Adapter: Calling generate_resume for {company_name}")
        result = generate_resume(
            job_description,
            company_name,
            company_info,
            bullet_file,
            job_change
        )
        logger.info(f"Adapter: Resume generation successful for {company_name}")
        return success(result)

    except FileOperationError as e:
        logger.error(f"Adapter: File operation error: {e}")
        return failure(
            f"File error: {e}\n\nPlease check that the bullet file exists and is readable.",
            error_type="file_error"
        )

    except ValidationError as e:
        logger.error(f"Adapter: Validation error: {e}")
        return failure(
            f"Validation error: {e}\n\nPlease check your input data.",
            error_type="validation_error"
        )

    except DataProcessingError as e:
        logger.error(f"Adapter: Data processing error: {e}")
        return failure(
            f"Processing error: {e}\n\nThe data could not be processed correctly.",
            error_type="processing_error"
        )

    except LLMServiceError as e:
        logger.error(f"Adapter: LLM service error: {e}")
        return failure(
            f"AI service error: {e}\n\nThe AI service encountered an error. Please try again.",
            error_type="llm_error"
        )

    except ResumeForgeError as e:
        logger.error(f"Adapter: Resume Forge error: {e}")
        return failure(
            f"Error: {e}",
            error_type="error"
        )

    except Exception as e:
        # Catch-all for unexpected errors
        logger.exception(f"Adapter: Unexpected error in generate_resume: {e}")
        return failure(
            f"Unexpected error: {e}\n\nPlease report this issue if it persists.",
            error_type="unexpected_error"
        )


def generate_cover_letter_adapter(
    resume_data: Dict[str, Any],
    job_title: str,
    job_description: str,
    company_name: str,
    company_info: str,
    job_change: bool,
    company_interest: Dict[str, str] = None,
    gap_explanation: str = None
) -> Result[str]:
    """
    Adapter for generate_cover_letter() - translates exceptions to Result types.

    Args:
        resume_data: Resume data dict containing summary and section bullets
        job_title: Target job title
        job_description: Target job description
        company_name: Target company name
        company_info: Information about the target company
        job_change: Boolean indicating if this is a career change
        company_interest: Optional dict with hook, alignment, credibility_anchor
        gap_explanation: Optional employment gap explanation text

    Returns:
        Success[str] containing HTML cover letter, or Failure with error message
    """
    try:
        logger.debug(f"Adapter: Calling generate_cover_letter for {job_title} at {company_name}")
        result = generate_cover_letter(
            resume_data,
            job_title,
            job_description,
            company_name,
            company_info,
            job_change,
            company_interest,
            gap_explanation
        )
        logger.info(f"Adapter: Cover letter generation successful")
        return success(result)

    except DataProcessingError as e:
        logger.error(f"Adapter: Data processing error: {e}")
        return failure(
            f"Processing error: {e}\n\nThe cover letter could not be generated correctly.",
            error_type="processing_error"
        )

    except LLMServiceError as e:
        logger.error(f"Adapter: LLM service error: {e}")
        return failure(
            f"AI service error: {e}\n\nThe AI service encountered an error. Please try again.",
            error_type="llm_error"
        )

    except ResumeForgeError as e:
        logger.error(f"Adapter: Resume Forge error: {e}")
        return failure(
            f"Error: {e}",
            error_type="error"
        )

    except Exception as e:
        # Catch-all for unexpected errors
        logger.exception(f"Adapter: Unexpected error in generate_cover_letter: {e}")
        return failure(
            f"Unexpected error: {e}\n\nPlease report this issue if it persists.",
            error_type="unexpected_error"
        )
