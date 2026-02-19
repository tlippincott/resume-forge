"""Unit tests for resume helper functions."""

import pytest
from pathlib import Path
from ui.resume_helpers import (
    build_html_bullets,
    bullets_to_text,
    text_to_bullets,
    load_resume_html,
    generate_pdf_file
)
from app.exceptions import FileOperationError


class TestBuildHtmlBullets:
    """Tests for build_html_bullets function."""

    def test_build_single_bullet(self):
        bullets = ["bullet 1"]
        result = build_html_bullets(bullets)
        assert result == "<li>bullet 1</li>"

    def test_build_multiple_bullets(self):
        bullets = ["bullet 1", "bullet 2", "bullet 3"]
        result = build_html_bullets(bullets)
        assert result == "<li>bullet 1</li>\n<li>bullet 2</li>\n<li>bullet 3</li>"

    def test_build_empty_list(self):
        result = build_html_bullets([])
        assert result == ""

    def test_build_with_whitespace_bullets(self):
        bullets = ["  bullet 1  ", "bullet 2"]
        result = build_html_bullets(bullets)
        assert result == "<li>bullet 1</li>\n<li>bullet 2</li>"

    def test_build_filters_empty_strings(self):
        bullets = ["bullet 1", "", "  ", "bullet 2"]
        result = build_html_bullets(bullets)
        assert result == "<li>bullet 1</li>\n<li>bullet 2</li>"


class TestBulletsToText:
    """Tests for bullets_to_text function."""

    def test_single_bullet(self):
        bullets = ["bullet 1"]
        result = bullets_to_text(bullets)
        assert result == "bullet 1"

    def test_multiple_bullets(self):
        bullets = ["bullet 1", "bullet 2", "bullet 3"]
        result = bullets_to_text(bullets)
        assert result == "bullet 1\nbullet 2\nbullet 3"

    def test_empty_list(self):
        result = bullets_to_text([])
        assert result == ""

    def test_filters_empty_strings(self):
        bullets = ["bullet 1", "", "  ", "bullet 2"]
        result = bullets_to_text(bullets)
        assert result == "bullet 1\nbullet 2"


class TestTextToBullets:
    """Tests for text_to_bullets function."""

    def test_single_line(self):
        text = "bullet 1"
        result = text_to_bullets(text)
        assert result == ["bullet 1"]

    def test_multiple_lines(self):
        text = "bullet 1\nbullet 2\nbullet 3"
        result = text_to_bullets(text)
        assert result == ["bullet 1", "bullet 2", "bullet 3"]

    def test_lines_with_blank_lines(self):
        text = "bullet 1\n\nbullet 2\n\n\nbullet 3"
        result = text_to_bullets(text)
        assert result == ["bullet 1", "bullet 2", "bullet 3"]

    def test_empty_string(self):
        result = text_to_bullets("")
        assert result == []

    def test_whitespace_only(self):
        result = text_to_bullets("   \n  \n  ")
        assert result == []

    def test_strips_whitespace(self):
        text = "  bullet 1  \n  bullet 2  "
        result = text_to_bullets(text)
        assert result == ["bullet 1", "bullet 2"]


class TestRoundTrip:
    """Test round-trip conversions."""

    def test_text_and_bullets_round_trip(self):
        original_bullets = ["bullet 1", "bullet 2", "bullet 3"]
        text = bullets_to_text(original_bullets)
        rebuilt_bullets = text_to_bullets(text)
        assert rebuilt_bullets == original_bullets


class TestLoadResumeHtml:
    """Tests for load_resume_html function."""

    def test_load_template_substitutes_placeholders(self):
        summary = "Test summary"
        spins_html = "<li>spins bullet</li>"
        programmer_html = "<li>programmer bullet</li>"
        analyst_html = "<li>analyst bullet</li>"

        result = load_resume_html(summary, spins_html, programmer_html, analyst_html)

        assert summary in result
        assert spins_html in result
        assert programmer_html in result
        assert analyst_html in result

    def test_load_template_removes_placeholders(self):
        result = load_resume_html("summary", "spins", "prog", "analyst")

        # Should not contain raw placeholders
        assert "{summary}" not in result
        assert "{spins}" not in result
        assert "{programmer}" not in result
        assert "{analyst}" not in result

    def test_load_template_handles_empty_values(self):
        result = load_resume_html("", "", "", "")

        # Should not error with empty strings
        assert isinstance(result, str)
        assert len(result) > 0  # Template structure should still exist

    def test_template_file_not_found(self):
        # Temporarily rename template to test error handling
        template_path = Path(__file__).parent.parent.parent / "templates" / "resume.html"
        backup_path = template_path.with_suffix('.html.bak')

        try:
            if template_path.exists():
                template_path.rename(backup_path)

            with pytest.raises(FileOperationError):
                load_resume_html("test", "test", "test", "test")
        finally:
            # Restore template
            if backup_path.exists():
                backup_path.rename(template_path)


class TestGeneratePdfFile:
    """Tests for generate_pdf_file function."""

    def test_generates_pdf_with_configured_name(self):
        html_content = "<html><body><h1>Test</h1></body></html>"

        result_path = generate_pdf_file(html_content)

        # Check file exists
        path = Path(result_path)
        assert path.exists()
        assert path.suffix == ".pdf"
        assert len(path.stem) > 0

        # Clean up
        path.unlink()

    def test_creates_output_directory(self):
        output_dir = Path(__file__).parent.parent.parent / "output"

        # Remove output dir if it exists for testing
        if output_dir.exists() and not any(output_dir.iterdir()):
            output_dir.rmdir()

        html_content = "<html><body><h1>Test</h1></body></html>"
        result_path = generate_pdf_file(html_content)

        # Check output directory was created
        assert output_dir.exists()
        assert output_dir.is_dir()

        # Clean up
        Path(result_path).unlink()

    def test_returns_absolute_path(self):
        html_content = "<html><body><h1>Test</h1></body></html>"

        result_path = generate_pdf_file(html_content)

        # Check path is absolute
        path = Path(result_path)
        assert path.is_absolute()

        # Clean up
        path.unlink()


class TestXSSPrevention:
    """Tests for XSS attack prevention through HTML escaping."""

    def test_build_html_bullets_escapes_script_tags(self):
        """Should escape <script> tags in bullets."""
        bullets = ["<script>alert('xss')</script>"]
        result = build_html_bullets(bullets)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result
        # Quotes are also escaped
        assert "alert" in result and ("&#x27;" in result or "&quot;" in result)

    def test_build_html_bullets_escapes_html_tags(self):
        """Should escape HTML tags like <b>, <i>, <img>."""
        bullets = [
            "<b>bold text</b>",
            "<i>italic text</i>",
            "<img src='x' />"
        ]
        result = build_html_bullets(bullets)
        assert "<b>" not in result
        assert "<i>" not in result
        assert "<img" not in result
        assert "&lt;b&gt;" in result
        assert "&lt;i&gt;" in result
        assert "&lt;img" in result

    def test_build_html_bullets_escapes_event_handlers(self):
        """Should escape event handlers like onclick, onerror."""
        bullets = [
            "<img src=x onerror='alert(1)'>",
            "<div onclick='alert(1)'>click</div>"
        ]
        result = build_html_bullets(bullets)
        # Tags should be escaped
        assert "&lt;img" in result
        assert "&lt;div" in result
        # The whole attack vector should be rendered harmless
        assert "<img src=" not in result
        assert "<div onclick=" not in result

    def test_build_html_bullets_escapes_attribute_injection(self):
        """Should escape quote characters to prevent attribute injection."""
        bullets = ['" onclick="alert(1)"']
        result = build_html_bullets(bullets)
        # Quote should be escaped
        assert '&quot;' in result or '&#x27;' in result
        # Should not have executable onclick
        assert 'onclick="alert' not in result

    def test_build_html_bullets_escapes_ampersands(self):
        """Should escape ampersands."""
        bullets = ["Research & Development"]
        result = build_html_bullets(bullets)
        assert "&amp;" in result or "Research &amp; Development" in result

    def test_load_resume_html_escapes_summary(self):
        """Should escape <script> tags in summary."""
        summary = "<script>alert('xss')</script>"
        result = load_resume_html(summary, "", "", "")
        # Script tag should be escaped in the output
        assert "<script>" not in result or result.count("<script>") == result.count("resume.js")
        # The escaped version should be present
        assert "&lt;script&gt;alert" in result

    def test_load_resume_html_escapes_summary_html_tags(self):
        """Should escape HTML tags in summary."""
        summary = "<b>Bold Summary</b>"
        result = load_resume_html(summary, "", "", "")
        # The literal <b> from summary should be escaped
        # (though template may have its own <b> tags)
        assert "&lt;b&gt;Bold Summary&lt;/b&gt;" in result

    def test_normal_text_preserved(self):
        """Should preserve normal text without corruption."""
        bullets = [
            "Developed Python APIs",
            "Managed 5TB+ databases",
            "Reduced downtime by 40%"
        ]
        result = build_html_bullets(bullets)
        # Normal text should be present
        assert "Developed Python APIs" in result
        assert "5TB+" in result
        assert "40%" in result
        # Should still have <li> tags (not escaped)
        assert result.startswith("<li>")
        assert "</li>" in result

    def test_xss_payload_combinations(self):
        """Should handle complex XSS attack combinations."""
        bullets = [
            "<img src=x onerror=\"alert('XSS')\">",
            "';alert(String.fromCharCode(88,83,83))//",
            "<iframe src='javascript:alert(1)'>",
            "<<SCRIPT>alert('XSS');//<</SCRIPT>"
        ]
        result = build_html_bullets(bullets)

        # No executable script elements
        assert "<img src=x onerror=" not in result
        assert "javascript:alert" not in result or "&lt;" in result
        # Tags should be escaped
        assert "&lt;" in result or all(bullet not in result for bullet in bullets)
