"""
Business layer exception hierarchy for Resume Forge.

This module defines typed exceptions that replace generic ValueError, TypeError,
and RuntimeError throughout the app layer. Each exception type represents a
specific category of business logic failure.
"""


class ResumeForgeError(Exception):
    """Base exception for all business logic errors in Resume Forge."""
    pass


class ValidationError(ResumeForgeError):
    """Data validation failures.

    Raised when input data fails validation rules (e.g., invalid formats,
    missing required fields, constraint violations).
    """
    pass


class FileOperationError(ResumeForgeError):
    """File I/O failures.

    Raised when file operations fail (e.g., file not found, permission denied,
    invalid file format, I/O errors).
    """
    pass


class DataProcessingError(ResumeForgeError):
    """Data transformation/processing failures.

    Raised when data processing operations fail (e.g., parsing errors,
    transformation failures, data corruption).
    """
    pass


class LLMServiceError(ResumeForgeError):
    """LLM API failures.

    Raised when LLM service calls fail (e.g., API errors, timeout errors,
    rate limit errors, invalid responses).
    """
    pass
