"""
Unit tests for app/distribution_engine.py

Tests:
- group_by_section(): groups analyzed bullets by section
- get_section_limits(): returns exact count for each section
- VALID_SECTIONS: contains correct sections
"""
import pytest
from app.distribution_engine import (
    group_by_section,
    get_section_limits,
    VALID_SECTIONS,
)


pytestmark = pytest.mark.unit


def make_analyzed_bullets(spins=0, programmer=0, analyst=0):
    """Helper to create analyzed bullet lists for testing."""
    bullets = []
    counter = 0
    for section, count in [("spins", spins), ("programmer", programmer), ("analyst", analyst)]:
        for i in range(count):
            bullets.append({
                "text": f"Bullet {counter + 1} for {section}",
                "section": section,
                "bullet_id": f"bullet_{counter:04d}",
            })
            counter += 1
    return bullets


class TestGroupBySection:
    """Tests for group_by_section function."""

    def test_groups_all_three_sections(self):
        """Should return dict with all three sections."""
        bullets = make_analyzed_bullets(spins=2, programmer=2, analyst=2)
        result = group_by_section(bullets)

        assert isinstance(result, dict)
        assert set(result.keys()) == {"spins", "programmer", "analyst"}

    def test_groups_bullets_correctly(self):
        """Should place bullets in their designated sections."""
        bullets = make_analyzed_bullets(spins=3, programmer=2, analyst=1)
        result = group_by_section(bullets)

        assert len(result["spins"]) == 3
        assert len(result["programmer"]) == 2
        assert len(result["analyst"]) == 1

    def test_returns_text_not_dicts(self):
        """Should return bullet text strings, not dicts."""
        bullets = make_analyzed_bullets(spins=1, programmer=1, analyst=1)
        result = group_by_section(bullets)

        for section_bullets in result.values():
            for bullet in section_bullets:
                assert isinstance(bullet, str)

    def test_preserves_order_within_section(self):
        """Should preserve bullet order within each section."""
        bullets = [
            {"text": "First spins", "section": "spins"},
            {"text": "First programmer", "section": "programmer"},
            {"text": "Second spins", "section": "spins"},
        ]
        result = group_by_section(bullets)

        assert result["spins"] == ["First spins", "Second spins"]
        assert result["programmer"] == ["First programmer"]
        assert result["analyst"] == []

    def test_empty_input_returns_empty_sections(self):
        """Should return empty lists for all sections when input is empty."""
        result = group_by_section([])

        assert result == {"spins": [], "programmer": [], "analyst": []}

    def test_handles_all_bullets_in_one_section(self):
        """Should handle all bullets going to a single section."""
        bullets = make_analyzed_bullets(spins=5, programmer=0, analyst=0)
        result = group_by_section(bullets)

        assert len(result["spins"]) == 5
        assert len(result["programmer"]) == 0
        assert len(result["analyst"]) == 0

    def test_unknown_section_routes_to_analyst(self):
        """Should route bullets with unknown sections to analyst."""
        bullets = [{"text": "Unknown bullet", "section": "unknown_section"}]
        result = group_by_section(bullets)

        assert "Unknown bullet" in result["analyst"]

    def test_missing_section_routes_to_analyst(self):
        """Should route bullets missing the section field to analyst."""
        bullets = [{"text": "No section bullet"}]
        result = group_by_section(bullets)

        assert "No section bullet" in result["analyst"]


class TestGetSectionLimits:
    """Tests for get_section_limits function."""

    def test_returns_tuple(self):
        """Should return a tuple."""
        result = get_section_limits("spins")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_raises_keyerror_for_invalid_section(self):
        """Should raise KeyError for invalid section name."""
        with pytest.raises(KeyError):
            get_section_limits("invalid_section")

        with pytest.raises(KeyError):
            get_section_limits("SPINS")

    def test_returns_count_for_all_sections(self):
        """Should return a count for each valid section."""
        for section in ["spins", "programmer", "analyst"]:
            count_min, count_max = get_section_limits(section)
            assert isinstance(count_min, int)
            assert isinstance(count_max, int)
            assert count_min == count_max
            assert count_min >= 1


class TestValidSections:
    """Tests for VALID_SECTIONS constant."""

    def test_has_required_sections(self):
        """Should contain all required sections."""
        assert "spins" in VALID_SECTIONS
        assert "programmer" in VALID_SECTIONS
        assert "analyst" in VALID_SECTIONS

    def test_is_a_set(self):
        """Should be a set for O(1) membership testing."""
        assert isinstance(VALID_SECTIONS, set)
