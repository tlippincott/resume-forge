"""
Unit tests for bullet library validation functions in app/bullet_library_manager.py

Tests:
- validate_bullet_item(): validates individual bullet items
- validate_bullet_library(): validates full bullet library dict
"""
import pytest
from app.bullet_library_manager import validate_bullet_item, validate_bullet_library


pytestmark = pytest.mark.unit


class TestValidateBulletItem:
    """Tests for validate_bullet_item function."""

    def test_valid_item_returns_no_errors(self):
        """Should return empty list for valid {text, section} dict."""
        item = {"text": "Resolved 50 support tickets daily", "section": "spins"}
        errors = validate_bullet_item(item, 0)
        assert errors == []

    def test_all_valid_sections_accepted(self):
        """Should accept spins, programmer, and analyst sections."""
        for section in ["spins", "programmer", "analyst"]:
            item = {"text": "Some bullet text", "section": section}
            errors = validate_bullet_item(item, 0)
            assert errors == [], f"Expected no errors for section '{section}'"

    def test_legacy_string_format_rejected(self):
        """Should reject plain strings (legacy format)."""
        errors = validate_bullet_item("plain string bullet", 0)
        assert len(errors) == 1
        assert "legacy" in errors[0].lower()

    def test_missing_text_field_rejected(self):
        """Should reject item missing 'text' field."""
        item = {"section": "spins"}
        errors = validate_bullet_item(item, 0)
        assert any("text" in e for e in errors)

    def test_empty_text_rejected(self):
        """Should reject item with empty 'text' field."""
        item = {"text": "", "section": "spins"}
        errors = validate_bullet_item(item, 0)
        assert any("text" in e for e in errors)

    def test_whitespace_only_text_rejected(self):
        """Should reject item with whitespace-only 'text' field."""
        item = {"text": "   ", "section": "spins"}
        errors = validate_bullet_item(item, 0)
        assert any("text" in e for e in errors)

    def test_missing_section_field_rejected(self):
        """Should reject item missing 'section' field."""
        item = {"text": "Some bullet text"}
        errors = validate_bullet_item(item, 0)
        assert any("section" in e for e in errors)

    def test_invalid_section_name_rejected(self):
        """Should reject item with invalid section name."""
        item = {"text": "Some bullet text", "section": "invalid_section"}
        errors = validate_bullet_item(item, 0)
        assert any("invalid" in e.lower() for e in errors)

    def test_case_sensitive_section_validation(self):
        """Should reject uppercase section names (sections are lowercase)."""
        item = {"text": "Some bullet text", "section": "SPINS"}
        errors = validate_bullet_item(item, 0)
        assert len(errors) > 0

    def test_non_dict_non_string_rejected(self):
        """Should reject non-dict, non-string items."""
        errors = validate_bullet_item(123, 0)
        assert len(errors) > 0

    def test_index_appears_in_error_messages(self):
        """Error messages should include the bullet index."""
        item = {"section": "spins"}  # Missing text
        errors = validate_bullet_item(item, 42)
        assert any("42" in e for e in errors)


class TestValidateBulletLibrary:
    """Tests for validate_bullet_library function."""

    def make_library(self, bullets):
        """Helper to create a bullet library dict."""
        return {"role": "Test Role", "bullets": bullets}

    def make_valid_bullet(self, section="spins"):
        return {"text": "Some bullet text for testing", "section": section}

    def test_valid_library_returns_true(self):
        """Should return (True, []) for a valid library."""
        bullets = [self.make_valid_bullet(s) for s in ["spins", "programmer", "analyst"]]
        is_valid, errors = validate_bullet_library(self.make_library(bullets))
        assert is_valid is True
        assert errors == []

    def test_missing_bullets_key_returns_false(self):
        """Should return (False, errors) when 'bullets' key is missing."""
        is_valid, errors = validate_bullet_library({"role": "Test"})
        assert is_valid is False
        assert len(errors) > 0

    def test_empty_bullets_list_returns_false(self):
        """Should return (False, errors) when bullets list is empty."""
        is_valid, errors = validate_bullet_library(self.make_library([]))
        assert is_valid is False
        assert len(errors) > 0

    def test_invalid_items_cause_failure(self):
        """Should return (False, errors) when items are invalid."""
        bullets = [
            "legacy string bullet",  # Invalid
            self.make_valid_bullet(),
        ]
        is_valid, errors = validate_bullet_library(self.make_library(bullets))
        assert is_valid is False
        assert len(errors) > 0

    def test_errors_capped_at_10(self):
        """Should stop collecting errors after 10 and add a truncation notice."""
        # Create 20 invalid bullets
        bullets = ["invalid string" for _ in range(20)]
        is_valid, errors = validate_bullet_library(self.make_library(bullets))
        assert is_valid is False
        # Should have at most 11 error messages (10 errors + truncation notice)
        assert len(errors) <= 11
        # Should indicate there are more errors
        assert any("stopping" in e.lower() or "..." in e for e in errors)

    def test_non_dict_input_returns_false(self):
        """Should return (False, errors) for non-dict input."""
        is_valid, errors = validate_bullet_library("not a dict")
        assert is_valid is False
        assert len(errors) > 0

    def test_non_list_bullets_returns_false(self):
        """Should return (False, errors) when bullets is not a list."""
        is_valid, errors = validate_bullet_library({"bullets": "not a list"})
        assert is_valid is False
        assert len(errors) > 0

    def test_multiple_invalid_items_all_reported(self):
        """Should report errors for all invalid items (up to cap)."""
        bullets = [{"section": "spins"} for _ in range(5)]  # All missing text
        is_valid, errors = validate_bullet_library(self.make_library(bullets))
        assert is_valid is False
        assert len(errors) >= 5
