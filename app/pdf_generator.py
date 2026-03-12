"""
PDF generation functions.

This module contains business logic for generating PDF files from HTML.
Previously in ui/resume_helpers.py.
"""

import shutil
from pathlib import Path
from app.render import render_html_to_pdf
from app.exceptions import FileOperationError
from app.logging_config import get_logger
from app.config import config

logger = get_logger(__name__)

def generate_pdf_file(html_content: str) -> str:
    """
    Generate PDF from HTML, return absolute file path.

    Args:
        html_content: Complete HTML document

    Returns:
        Absolute path to generated PDF file

    Raises:
        FileOperationError: If PDF generation fails
    """
    filename = f"{config.output.resume_pdf_name}.pdf"

    # Ensure output directory exists
    output_dir = Path(__file__).parent.parent / "output" / "resumes"
    try:
        output_dir.mkdir(exist_ok=True)
    except OSError as e:
        logger.error(f"Error creating output directory: {e}")
        raise FileOperationError(f"Error creating output directory: {e}")

    # Create full path
    filepath = output_dir / filename

    # Generate PDF
    try:
        render_html_to_pdf(html_content, str(filepath))
        logger.info(f"Resume PDF generated: {filepath}")
        if config.output.pdf_copy_dir:
            copy_dir = Path(config.output.pdf_copy_dir)
            copy_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(filepath, copy_dir / config.output.pdf_copy_resume_name)
            logger.info(f"Resume PDF copied to {copy_dir}")
    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        raise FileOperationError(f"Error generating PDF: {e}")

    # Return absolute path
    return str(filepath.absolute())


def generate_cover_letter_pdf_file(html_content: str) -> str:
    """
    Generate cover letter PDF from HTML, return absolute file path.

    Args:
        html_content: Complete HTML document

    Returns:
        Absolute path to generated PDF file

    Raises:
        FileOperationError: If PDF generation fails
    """
    filename = f"{config.output.cover_letter_pdf_name}.pdf"

    # Ensure output directory exists
    output_dir = Path(__file__).parent.parent / "output" / "cover_letters"
    try:
        output_dir.mkdir(exist_ok=True)
    except OSError as e:
        logger.error(f"Error creating output directory: {e}")
        raise FileOperationError(f"Error creating output directory: {e}")

    # Create full path
    filepath = output_dir / filename

    # Generate PDF
    try:
        render_html_to_pdf(html_content, str(filepath))
        logger.info(f"Cover letter PDF generated: {filepath}")
        if config.output.pdf_copy_dir:
            copy_dir = Path(config.output.pdf_copy_dir)
            copy_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(filepath, copy_dir / config.output.pdf_copy_cover_letter_name)
            logger.info(f"Cover letter PDF copied to {copy_dir}")
    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        raise FileOperationError(f"Error generating PDF: {e}")

    # Return absolute path
    return str(filepath.absolute())
