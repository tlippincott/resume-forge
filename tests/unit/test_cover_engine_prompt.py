"""
Unit tests for cover_letter_prompt in app/cover_engine.py

Tests the pure prompt generation function separately from the
integration behavior of generate_cover_letter.
"""
import pytest
from app.cover_engine import cover_letter_prompt


pytestmark = pytest.mark.unit


class TestCoverLetterPrompt:
    """Tests for cover_letter_prompt function."""

    @pytest.fixture
    def prompt_args(self, sample_bullets):
        """Standard arguments for cover_letter_prompt."""
        return {
            "summary": "Experienced software engineer with Python expertise.",
            "bullets": sample_bullets,
            "job_title": "Senior Software Engineer",
            "job_description": "We are looking for a Python developer...",
            "company_name": "TechCorp",
            "company_info": "A leading cloud solutions provider.",
            "job_change": False
        }

    def test_returns_list(self, prompt_args):
        """Should return a list of message dicts."""
        result = cover_letter_prompt(**prompt_args)

        assert isinstance(result, list)
        assert len(result) == 1

    def test_has_user_role(self, prompt_args):
        """Should have user role in the message."""
        result = cover_letter_prompt(**prompt_args)

        assert result[0]["role"] == "user"

    def test_includes_summary(self, prompt_args):
        """Should include the professional summary."""
        result = cover_letter_prompt(**prompt_args)
        content = result[0]["content"]

        assert prompt_args["summary"] in content
        assert "PROFESSIONAL SUMMARY:" in content

    def test_includes_bullets(self, prompt_args):
        """Should include resume bullets."""
        result = cover_letter_prompt(**prompt_args)
        content = result[0]["content"]

        assert str(prompt_args["bullets"]) in content
        assert "RESUME BULLETS:" in content

    def test_includes_job_title(self, prompt_args):
        """Should include job title."""
        result = cover_letter_prompt(**prompt_args)
        content = result[0]["content"]

        assert prompt_args["job_title"] in content
        assert "JOB TITLE:" in content

    def test_includes_job_description(self, prompt_args):
        """Should include job description."""
        result = cover_letter_prompt(**prompt_args)
        content = result[0]["content"]

        assert prompt_args["job_description"] in content
        assert "JOB DESCRIPTION:" in content

    def test_includes_company_name(self, prompt_args):
        """Should include company name."""
        result = cover_letter_prompt(**prompt_args)
        content = result[0]["content"]

        assert prompt_args["company_name"] in content
        assert "COMPANY NAME:" in content

    def test_includes_company_info(self, prompt_args):
        """Should include company info."""
        result = cover_letter_prompt(**prompt_args)
        content = result[0]["content"]

        assert prompt_args["company_info"] in content
        assert "COMPANY INFO:" in content

    def test_includes_job_change_context(self, prompt_args):
        """Should include job change context."""
        result = cover_letter_prompt(**prompt_args)
        content = result[0]["content"]

        assert str(prompt_args["job_change"]) in content
        assert "JOB CHANGE CONTEXT:" in content

    def test_includes_cover_letter_body_schema(self, prompt_args):
        """Should include expected JSON schema for cover_letter_body."""
        result = cover_letter_prompt(**prompt_args)
        content = result[0]["content"]

        assert "cover_letter_body" in content
        assert "3 paragraphs" in content or "Exactly 3" in content

    def test_includes_paragraph_structure_requirements(self, prompt_args):
        """Should include requirements for paragraph structure."""
        result = cover_letter_prompt(**prompt_args)
        content = result[0]["content"]

        # Check for paragraph guidance
        assert "opening" in content.lower() or "paragraph 1" in content.lower()
        assert "body" in content.lower() or "paragraph 2" in content.lower()
        assert "closing" in content.lower() or "paragraph 3" in content.lower()

    def test_includes_truth_preserving_rules(self, prompt_args):
        """Should include anti-hallucination rules."""
        result = cover_letter_prompt(**prompt_args)
        content = result[0]["content"]

        # Should have rules against fabrication
        assert "Do NOT" in content or "MUST NOT" in content
        assert "invent" in content.lower() or "fabricat" in content.lower()

    def test_includes_word_count_guidance(self, prompt_args):
        """Should include word count guidance for paragraphs."""
        result = cover_letter_prompt(**prompt_args)
        content = result[0]["content"]

        # Check for word count mentions
        assert "words" in content.lower()

    def test_job_change_true_context(self, prompt_args):
        """Should handle job_change=True context."""
        prompt_args["job_change"] = True
        result = cover_letter_prompt(**prompt_args)
        content = result[0]["content"]

        assert "True" in content

    def test_job_change_false_context(self, prompt_args):
        """Should handle job_change=False context."""
        prompt_args["job_change"] = False
        result = cover_letter_prompt(**prompt_args)
        content = result[0]["content"]

        assert "False" in content

    def test_handles_empty_company_info(self, prompt_args):
        """Should handle empty company info gracefully."""
        prompt_args["company_info"] = ""
        result = cover_letter_prompt(**prompt_args)

        # Should not raise, should still return valid structure
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["role"] == "user"
