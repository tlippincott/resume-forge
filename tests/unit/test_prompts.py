"""
Unit tests for app/prompts.py

Tests the pure prompt generation functions:
- bullet_selection_prompt()
- rewrite_prompt()
"""
import pytest
from app.prompts import bullet_selection_prompt, rewrite_prompt


pytestmark = pytest.mark.unit


class TestBulletSelectionPrompt:
    """Tests for bullet_selection_prompt function."""

    def test_returns_list(self, sample_job_description, sample_bullets):
        """Should return a list of message dicts."""
        result = bullet_selection_prompt(sample_job_description, sample_bullets)

        assert isinstance(result, list)
        assert len(result) == 1

    def test_has_user_role(self, sample_job_description, sample_bullets):
        """Should have user role in the message."""
        result = bullet_selection_prompt(sample_job_description, sample_bullets)

        assert result[0]["role"] == "user"

    def test_includes_job_description(self, sample_job_description, sample_bullets):
        """Should include job description in content."""
        result = bullet_selection_prompt(sample_job_description, sample_bullets)
        content = result[0]["content"]

        assert sample_job_description in content
        assert "JOB DESCRIPTION:" in content

    def test_includes_bullets(self, sample_job_description, sample_bullets):
        """Should include bullets in content."""
        result = bullet_selection_prompt(sample_job_description, sample_bullets)
        content = result[0]["content"]

        assert str(sample_bullets) in content
        assert "BULLETS:" in content

    def test_includes_json_schema(self, sample_job_description, sample_bullets):
        """Should include expected JSON schema."""
        result = bullet_selection_prompt(sample_job_description, sample_bullets)
        content = result[0]["content"]

        assert "scored_bullets" in content
        assert '"bullet"' in content
        assert '"score"' in content

    def test_includes_scoring_guide(self, sample_job_description, sample_bullets):
        """Should include scoring instructions."""
        result = bullet_selection_prompt(sample_job_description, sample_bullets)
        content = result[0]["content"]

        assert "SCORING GUIDE:" in content
        assert "0-5" in content or "0–5" in content


class TestRewritePrompt:
    """Tests for rewrite_prompt function."""

    def test_returns_list(self, sample_job_description, sample_bullets):
        """Should return a list of message dicts."""
        result = rewrite_prompt(
            sample_job_description,
            "TechCorp",
            "A tech company",
            sample_bullets,
            False
        )

        assert isinstance(result, list)
        assert len(result) == 1

    def test_has_user_role(self, sample_job_description, sample_bullets):
        """Should have user role in the message."""
        result = rewrite_prompt(
            sample_job_description,
            "TechCorp",
            "A tech company",
            sample_bullets,
            False
        )

        assert result[0]["role"] == "user"

    def test_includes_all_parameters(self, sample_job_description, sample_bullets):
        """Should include all input parameters in content."""
        company_name = "TechCorp"
        company_info = "A tech company"
        job_change = True

        result = rewrite_prompt(
            sample_job_description,
            company_name,
            company_info,
            sample_bullets,
            job_change
        )
        content = result[0]["content"]

        assert sample_job_description in content
        assert company_name in content
        assert company_info in content
        assert str(sample_bullets) in content
        assert str(job_change) in content

    def test_includes_output_schema(self, sample_job_description, sample_bullets):
        """Should include expected JSON output schema."""
        result = rewrite_prompt(
            sample_job_description,
            "TechCorp",
            "A tech company",
            sample_bullets,
            False
        )
        content = result[0]["content"]

        assert "rewritten_bullets" in content
        assert "summary" in content

    def test_includes_truth_preserving_rules(self, sample_job_description, sample_bullets):
        """Should include rules to prevent hallucination."""
        result = rewrite_prompt(
            sample_job_description,
            "TechCorp",
            "A tech company",
            sample_bullets,
            False
        )
        content = result[0]["content"]

        # Check for anti-hallucination rules
        assert "MUST NOT" in content or "Do NOT" in content
        assert "invent" in content.lower() or "invention" in content.lower()

    def test_includes_verification_checklist(self, sample_job_description, sample_bullets):
        """Should include verification checklist."""
        result = rewrite_prompt(
            sample_job_description,
            "TechCorp",
            "A tech company",
            sample_bullets,
            False
        )
        content = result[0]["content"]

        assert "VERIFICATION CHECKLIST" in content


