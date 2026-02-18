"""
Unit tests for section-aware bullet selection in app/resume_engine.py

Tests:
- select_bullets_by_section(): selects top-scoring bullets per section
"""
import pytest
from app.resume_engine import select_bullets_by_section
from app.exceptions import ValidationError


pytestmark = pytest.mark.unit


def make_bullet_items(spins=0, programmer=0, analyst=0, prefix="Bullet"):
    """Helper to create BulletLibraryItem lists."""
    items = []
    counter = 0
    for section, count in [("spins", spins), ("programmer", programmer), ("analyst", analyst)]:
        for i in range(count):
            items.append({"text": f"{prefix} {counter + 1} for {section}", "section": section})
            counter += 1
    return items


def make_scored(bullet_items, base_score=3.0):
    """Helper to create scored bullet list matching bullet_items."""
    return [
        {"bullet": item["text"], "score": base_score - i * 0.01}
        for i, item in enumerate(bullet_items)
    ]


class TestSelectBulletsBySection:
    """Tests for select_bullets_by_section function."""

    def test_returns_exact_counts(self, mocker):
        """Should return exactly spins_count + programmer_count + analyst_count bullets."""
        mocker.patch("app.resume_engine.config.business.spins_count", 12)
        mocker.patch("app.resume_engine.config.business.programmer_count", 12)
        mocker.patch("app.resume_engine.config.business.analyst_count", 10)

        items = make_bullet_items(spins=20, programmer=20, analyst=15)
        scored = make_scored(items)

        result = select_bullets_by_section(scored, items)

        spins_selected = [r for r in result if r["section"] == "spins"]
        programmer_selected = [r for r in result if r["section"] == "programmer"]
        analyst_selected = [r for r in result if r["section"] == "analyst"]

        assert len(spins_selected) == 12
        assert len(programmer_selected) == 12
        assert len(analyst_selected) == 10
        assert len(result) == 34

    def test_picks_highest_scoring_bullets(self, mocker):
        """Should select bullets with highest scores within each section."""
        mocker.patch("app.resume_engine.config.business.spins_count", 2)
        mocker.patch("app.resume_engine.config.business.programmer_count", 2)
        mocker.patch("app.resume_engine.config.business.analyst_count", 2)

        items = [
            {"text": "Low spins", "section": "spins"},
            {"text": "High spins A", "section": "spins"},
            {"text": "High spins B", "section": "spins"},
            {"text": "Low programmer", "section": "programmer"},
            {"text": "High programmer A", "section": "programmer"},
            {"text": "High programmer B", "section": "programmer"},
            {"text": "Low analyst", "section": "analyst"},
            {"text": "High analyst A", "section": "analyst"},
            {"text": "High analyst B", "section": "analyst"},
        ]
        # Give "High" bullets higher scores than "Low" bullets
        scored = [
            {"bullet": "Low spins", "score": 1.0},
            {"bullet": "High spins A", "score": 5.0},
            {"bullet": "High spins B", "score": 4.0},
            {"bullet": "Low programmer", "score": 1.0},
            {"bullet": "High programmer A", "score": 5.0},
            {"bullet": "High programmer B", "score": 4.0},
            {"bullet": "Low analyst", "score": 1.0},
            {"bullet": "High analyst A", "score": 5.0},
            {"bullet": "High analyst B", "score": 4.0},
        ]

        result = select_bullets_by_section(scored, items)
        selected_texts = {r["text"] for r in result}

        assert "High spins A" in selected_texts
        assert "High spins B" in selected_texts
        assert "Low spins" not in selected_texts

        assert "High programmer A" in selected_texts
        assert "High programmer B" in selected_texts
        assert "Low programmer" not in selected_texts

        assert "High analyst A" in selected_texts
        assert "High analyst B" in selected_texts
        assert "Low analyst" not in selected_texts

    def test_insufficient_spins_raises_validation_error(self, mocker):
        """Should raise ValidationError when spins section has too few bullets."""
        mocker.patch("app.resume_engine.config.business.spins_count", 12)
        mocker.patch("app.resume_engine.config.business.programmer_count", 12)
        mocker.patch("app.resume_engine.config.business.analyst_count", 10)

        # Only 5 spins bullets, need 12
        items = make_bullet_items(spins=5, programmer=15, analyst=15)
        scored = make_scored(items)

        with pytest.raises(ValidationError, match="spins"):
            select_bullets_by_section(scored, items)

    def test_insufficient_programmer_raises_validation_error(self, mocker):
        """Should raise ValidationError when programmer section has too few bullets."""
        mocker.patch("app.resume_engine.config.business.spins_count", 12)
        mocker.patch("app.resume_engine.config.business.programmer_count", 12)
        mocker.patch("app.resume_engine.config.business.analyst_count", 10)

        # Only 5 programmer bullets, need 12
        items = make_bullet_items(spins=15, programmer=5, analyst=15)
        scored = make_scored(items)

        with pytest.raises(ValidationError, match="programmer"):
            select_bullets_by_section(scored, items)

    def test_insufficient_analyst_raises_validation_error(self, mocker):
        """Should raise ValidationError when analyst section has too few bullets."""
        mocker.patch("app.resume_engine.config.business.spins_count", 12)
        mocker.patch("app.resume_engine.config.business.programmer_count", 12)
        mocker.patch("app.resume_engine.config.business.analyst_count", 10)

        # Only 3 analyst bullets, need 10
        items = make_bullet_items(spins=15, programmer=15, analyst=3)
        scored = make_scored(items)

        with pytest.raises(ValidationError, match="analyst"):
            select_bullets_by_section(scored, items)

    def test_error_message_includes_count_info(self, mocker):
        """ValidationError message should include actual vs required counts."""
        mocker.patch("app.resume_engine.config.business.spins_count", 12)
        mocker.patch("app.resume_engine.config.business.programmer_count", 12)
        mocker.patch("app.resume_engine.config.business.analyst_count", 10)

        items = make_bullet_items(spins=8, programmer=15, analyst=15)
        scored = make_scored(items)

        with pytest.raises(ValidationError) as exc_info:
            select_bullets_by_section(scored, items)

        error_msg = str(exc_info.value)
        # Should mention actual count (8) and required count (12)
        assert "8" in error_msg
        assert "12" in error_msg

    def test_bullets_with_missing_scores_get_zero(self, mocker):
        """Bullets not in scored list should receive score 0.0."""
        mocker.patch("app.resume_engine.config.business.spins_count", 1)
        mocker.patch("app.resume_engine.config.business.programmer_count", 1)
        mocker.patch("app.resume_engine.config.business.analyst_count", 1)

        items = [
            {"text": "Scored spins", "section": "spins"},
            {"text": "Unscored spins", "section": "spins"},
            {"text": "Scored programmer", "section": "programmer"},
            {"text": "Unscored programmer", "section": "programmer"},
            {"text": "Scored analyst", "section": "analyst"},
            {"text": "Unscored analyst", "section": "analyst"},
        ]
        scored = [
            {"bullet": "Scored spins", "score": 5.0},
            {"bullet": "Scored programmer", "score": 5.0},
            {"bullet": "Scored analyst", "score": 5.0},
            # Unscored bullets not in list
        ]

        result = select_bullets_by_section(scored, items)
        selected_texts = {r["text"] for r in result}

        # Higher-scored bullets should be selected
        assert "Scored spins" in selected_texts
        assert "Scored programmer" in selected_texts
        assert "Scored analyst" in selected_texts
