"""
Unit tests for app/distribution_engine.py

Tests the deterministic functions:
- validate_assignments()
- validate_section_distribution()
- rebalance()
- get_section_limits()
"""
import pytest
from app.distribution_engine import (
    validate_assignments,
    validate_section_distribution,
    rebalance,
    get_section_limits,
    SECTION_CONFIG,
    VALID_SECTIONS,
)
from app.exceptions import ValidationError


pytestmark = pytest.mark.unit


class TestValidateAssignments:
    """Tests for validate_assignments function."""

    def test_valid_assignments_pass(self, valid_assignments):
        """Should not raise for valid assignments."""
        # Should not raise
        validate_assignments(valid_assignments)

    def test_raises_typeerror_for_non_list(self):
        """Should raise ValidationError when assignments is not a list."""
        with pytest.raises(ValidationError, match="Expected list"):
            validate_assignments("not a list")

        with pytest.raises(ValidationError, match="Expected list"):
            validate_assignments({"assignments": []})

        with pytest.raises(ValidationError, match="Expected list"):
            validate_assignments(None)

    def test_raises_valueerror_for_empty_list(self):
        """Should raise ValidationError for empty list."""
        with pytest.raises(ValidationError, match="empty"):
            validate_assignments([])

    def test_raises_typeerror_for_non_dict_items(self):
        """Should raise ValidationError when assignment items are not dicts."""
        with pytest.raises(ValidationError, match="not a dict"):
            validate_assignments(["not a dict"])

        with pytest.raises(ValidationError, match="not a dict"):
            validate_assignments([{"bullet": "test", "section": "spins"}, "invalid"])

    def test_raises_valueerror_for_missing_bullet_key(self):
        """Should raise ValidationError when 'bullet' key is missing."""
        with pytest.raises(ValidationError, match="missing 'bullet' key"):
            validate_assignments([{"section": "spins"}])

    def test_raises_valueerror_for_missing_section_key(self):
        """Should raise ValidationError when 'section' key is missing."""
        with pytest.raises(ValidationError, match="missing 'section' key"):
            validate_assignments([{"bullet": "test bullet"}])

    def test_raises_typeerror_for_non_string_bullet(self):
        """Should raise ValidationError when bullet is not a string."""
        with pytest.raises(ValidationError, match="bullet is not string"):
            validate_assignments([{"bullet": 123, "section": "spins"}])

    def test_raises_valueerror_for_empty_bullet(self):
        """Should raise ValidationError for empty or whitespace-only bullet."""
        with pytest.raises(ValidationError, match="empty bullet"):
            validate_assignments([{"bullet": "", "section": "spins"}])

        with pytest.raises(ValidationError, match="empty bullet"):
            validate_assignments([{"bullet": "   ", "section": "spins"}])

    def test_raises_valueerror_for_invalid_section(self):
        """Should raise ValidationError for invalid section names."""
        with pytest.raises(ValidationError, match="invalid section"):
            validate_assignments([{"bullet": "test", "section": "invalid_section"}])

        with pytest.raises(ValidationError, match="invalid section"):
            validate_assignments([{"bullet": "test", "section": "SPINS"}])  # Case sensitive

    def test_accepts_all_valid_sections(self, make_assignments):
        """Should accept all valid section names."""
        for section in VALID_SECTIONS:
            assignments = [{"bullet": "test bullet", "section": section}]
            validate_assignments(assignments)  # Should not raise


class TestValidateSectionDistribution:
    """Tests for validate_section_distribution function."""

    def test_valid_distribution_passes(self):
        """Should not raise for valid distributions."""
        sections = {
            "spins": ["b"] * 10,
            "programmer": ["b"] * 12,
            "analyst": ["b"] * 5
        }
        # Should not raise
        validate_section_distribution(sections)

    def test_enforces_minimum_for_primary_sections(self):
        """Should raise ValidationError when primary sections have fewer than minimum."""
        # spins requires min 10
        with pytest.raises(ValidationError, match="requires minimum 10"):
            validate_section_distribution({
                "spins": ["b"] * 9,
                "programmer": ["b"] * 10,
                "analyst": []
            })

        # programmer requires min 10
        with pytest.raises(ValidationError, match="requires minimum 10"):
            validate_section_distribution({
                "spins": ["b"] * 10,
                "programmer": ["b"] * 5,
                "analyst": []
            })

    def test_enforces_maximum_for_primary_sections(self):
        """Should raise ValidationError when primary sections exceed maximum."""
        # spins max is 12
        with pytest.raises(ValidationError, match="requires maximum 12"):
            validate_section_distribution({
                "spins": ["b"] * 15,
                "programmer": ["b"] * 10,
                "analyst": []
            })

        # programmer max is 12
        with pytest.raises(ValidationError, match="requires maximum 12"):
            validate_section_distribution({
                "spins": ["b"] * 10,
                "programmer": ["b"] * 13,
                "analyst": []
            })

    def test_analyst_has_no_limits(self):
        """Should allow any number of bullets in analyst section."""
        # Zero bullets
        validate_section_distribution({
            "spins": ["b"] * 10,
            "programmer": ["b"] * 10,
            "analyst": []
        })

        # Many bullets
        validate_section_distribution({
            "spins": ["b"] * 10,
            "programmer": ["b"] * 10,
            "analyst": ["b"] * 100
        })


class TestRebalance:
    """Tests for rebalance function."""

    def test_returns_three_section_dict(self, make_assignments):
        """Should return dict with all three sections."""
        assignments = make_assignments(spins=10, programmer=10, analyst=5)
        result = rebalance(assignments)

        assert isinstance(result, dict)
        assert set(result.keys()) == {"spins", "programmer", "analyst"}

    def test_preserves_balanced_distribution(self, make_assignments):
        """Should preserve distribution when already balanced."""
        assignments = make_assignments(spins=10, programmer=10, analyst=5)
        result = rebalance(assignments)

        assert len(result["spins"]) == 10
        assert len(result["programmer"]) == 10
        assert len(result["analyst"]) == 5

    def test_handles_overflow_to_analyst(self, make_assignments):
        """Should move overflow from primary sections to analyst."""
        # 15 spins exceeds max of 12
        assignments = make_assignments(spins=15, programmer=10, analyst=0)
        result = rebalance(assignments)

        assert len(result["spins"]) == 12  # Max enforced
        assert len(result["programmer"]) == 10
        assert len(result["analyst"]) == 3  # Overflow moved here

    def test_enforces_minimum_by_pulling_from_analyst(self, make_assignments):
        """Should pull bullets from analyst to meet primary section minimums."""
        # Only 5 spins, needs 10; analyst has 10
        assignments = make_assignments(spins=5, programmer=10, analyst=10)
        result = rebalance(assignments)

        assert len(result["spins"]) == 10  # Min enforced
        assert len(result["programmer"]) == 10
        assert len(result["analyst"]) == 5  # 5 pulled to spins

    def test_both_sections_can_pull_from_analyst(self, make_assignments):
        """Should handle both primary sections needing to pull from analyst."""
        # Both under minimum, analyst has extras
        assignments = make_assignments(spins=5, programmer=5, analyst=15)
        result = rebalance(assignments)

        assert len(result["spins"]) == 10
        assert len(result["programmer"]) == 10
        # Started with 5+5+15=25, after: 10+10+analyst=25, so analyst=5
        assert len(result["analyst"]) == 5

    def test_total_bullets_preserved(self, make_assignments):
        """Should preserve total bullet count."""
        assignments = make_assignments(spins=15, programmer=15, analyst=5)
        total_input = len(assignments)

        result = rebalance(assignments)
        total_output = sum(len(bullets) for bullets in result.values())

        assert total_output == total_input

    def test_bullet_content_preserved(self, make_assignments):
        """Should preserve actual bullet text content."""
        custom_bullets = ["Bullet A", "Bullet B", "Bullet C", "Bullet D", "Bullet E"]
        assignments = make_assignments(spins=2, programmer=2, analyst=1, bullets=custom_bullets)

        result = rebalance(assignments)
        all_output_bullets = []
        for bullets in result.values():
            all_output_bullets.extend(bullets)

        # All original bullets should be present
        for bullet in custom_bullets:
            assert bullet in all_output_bullets

    def test_validates_input(self):
        """Should validate input assignments."""
        with pytest.raises(ValidationError):
            rebalance("not a list")

        with pytest.raises(ValidationError):
            rebalance([])

    def test_handles_edge_case_empty_analyst(self, make_assignments):
        """Should handle case where analyst is empty."""
        assignments = make_assignments(spins=10, programmer=10, analyst=0)
        result = rebalance(assignments)

        assert len(result["spins"]) == 10
        assert len(result["programmer"]) == 10
        assert len(result["analyst"]) == 0

    def test_handles_edge_case_insufficient_bullets(self, make_assignments):
        """Should handle case where not enough bullets exist to meet minimums."""
        # Only 15 total bullets, can't meet both minimums (10+10=20)
        assignments = make_assignments(spins=8, programmer=7, analyst=0)
        result = rebalance(assignments)

        # Should still work, just not meet minimums
        total = sum(len(b) for b in result.values())
        assert total == 15


class TestGetSectionLimits:
    """Tests for get_section_limits function."""

    def test_returns_tuple(self):
        """Should return a tuple of (min, max)."""
        result = get_section_limits("spins")

        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_spins_limits(self):
        """Should return correct limits for spins."""
        min_val, max_val = get_section_limits("spins")

        assert min_val == 10
        assert max_val == 12

    def test_programmer_limits(self):
        """Should return correct limits for programmer."""
        min_val, max_val = get_section_limits("programmer")

        assert min_val == 10
        assert max_val == 12

    def test_analyst_limits(self):
        """Should return correct limits for analyst (unlimited)."""
        min_val, max_val = get_section_limits("analyst")

        assert min_val == 0
        assert max_val is None  # Unlimited

    def test_raises_keyerror_for_invalid_section(self):
        """Should raise KeyError for invalid section name."""
        with pytest.raises(KeyError):
            get_section_limits("invalid_section")

        with pytest.raises(KeyError):
            get_section_limits("SPINS")  # Case sensitive


class TestSectionConfig:
    """Tests for SECTION_CONFIG constant."""

    def test_has_required_sections(self):
        """Should have all required sections."""
        assert "spins" in SECTION_CONFIG
        assert "programmer" in SECTION_CONFIG
        assert "analyst" in SECTION_CONFIG

    def test_primary_sections_have_limits(self):
        """Primary sections should have min and max limits."""
        for section in ["spins", "programmer"]:
            config = SECTION_CONFIG[section]
            assert config["min_bullets"] > 0
            assert config["max_bullets"] is not None
            assert config["priority"] == "primary"

    def test_analyst_is_overflow_section(self):
        """Analyst should be the overflow section with no upper limit."""
        config = SECTION_CONFIG["analyst"]
        assert config["min_bullets"] == 0
        assert config["max_bullets"] is None
        assert config["priority"] == "overflow"
