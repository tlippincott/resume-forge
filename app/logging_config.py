"""
Application-wide logging configuration for Resume Forge.

This module configures structured logging that outputs to both console and file,
enabling better debugging and error tracking across all layers.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logging(
    log_level: int = logging.INFO,
    log_file: str = "resume_forge.log",
    log_dir: str = "logs"
) -> logging.Logger:
    """Configure application-wide logging.

    Args:
        log_level: Logging level (default: INFO)
        log_file: Log filename (default: "resume_forge.log")
        log_dir: Log directory (default: "logs")

    Returns:
        Configured root logger
    """
    # Create logs directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    # Create log file path with timestamp
    timestamp = datetime.now().strftime("%Y%m%d")
    log_file_path = log_path / f"{timestamp}_{log_file}"

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_formatter = logging.Formatter(
        fmt='%(levelname)s - %(name)s - %(message)s'
    )

    # Console handler (INFO and above)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler (DEBUG and above)
    file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)

    # Log startup message
    root_logger.info(f"Logging initialized - Log file: {log_file_path}")

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module.

    Args:
        name: Logger name (typically __name__ of the module)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Initialize logging on module import
_root_logger = setup_logging()
