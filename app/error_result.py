"""
Result types for app layer → UI layer boundary.

This module provides Success and Failure types that replace inconsistent
tuple returns (bool, str), (str, str, str), etc. throughout the UI boundary.
Result types enable consistent error handling and eliminate silent failures.
"""

from typing import TypeVar, Generic, Union
from dataclasses import dataclass


T = TypeVar('T')


@dataclass
class Success(Generic[T]):
    """Successful operation result containing a value.

    Attributes:
        value: The successful result value of type T
    """
    value: T

    def is_success(self) -> bool:
        """Check if result is success (always True)."""
        return True

    def is_failure(self) -> bool:
        """Check if result is failure (always False)."""
        return False


@dataclass
class Failure:
    """Failed operation result containing error information.

    Attributes:
        error_message: Human-readable error message for UI display
        error_type: Error category (e.g., "error", "warning", "validation_error")
    """
    error_message: str
    error_type: str = "error"

    def is_success(self) -> bool:
        """Check if result is success (always False)."""
        return False

    def is_failure(self) -> bool:
        """Check if result is failure (always True)."""
        return True


# Union type for all result types
Result = Union[Success[T], Failure]


# Convenience constructors
def success(value: T) -> Success[T]:
    """Create a successful result.

    Args:
        value: The success value

    Returns:
        Success instance containing the value
    """
    return Success(value)


def failure(error_message: str, error_type: str = "error") -> Failure:
    """Create a failed result.

    Args:
        error_message: Human-readable error message
        error_type: Error category (default: "error")

    Returns:
        Failure instance containing error information
    """
    return Failure(error_message, error_type)
