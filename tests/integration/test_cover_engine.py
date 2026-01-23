"""
Integration tests for app/cover_engine.py

Tests generate_cover_letter with mocked OpenAI calls:
- Full pipeline flow
- Output format validation
- Temperature setting
"""
import pytest
from app.cover_engine import generate_cover_letter


pytestmark = pytest.mark.integration


class TestGenerateCoverLetter:
    """Tests for generate_cover_letter function."""

    @pytest.fixture
    def resume_data(self):
        """Sample resume data structure."""
        return {
            "summary": "Experienced software engineer with Python and cloud expertise.",
            "spins": ["Resolved customer technical issues", "Collaborated with support teams"],
            "programmer": ["Built REST APIs with Python", "Automated deployment pipelines"],
            "analyst": ["Analyzed system performance", "Created technical documentation"]
        }

    @pytest.fixture
    def cover_letter_response(self):
        """Mock response for cover letter generation."""
        return {
            "cover_letter_body": [
                "First paragraph introducing myself and expressing interest in the role at TechCorp.",
                "Second paragraph connecting my experience in Python development and API design to the job requirements. I have worked on similar technical challenges.",
                "Third paragraph closing with genuine interest in the specific opportunity."
            ]
        }

    def test_returns_html_paragraphs(self, mocker, resume_data, cover_letter_response):
        """Should return cover letter formatted as HTML paragraphs."""
        mock_call = mocker.patch("app.cover_engine.call_openai_json")
        mock_call.return_value = cover_letter_response

        result = generate_cover_letter(
            resume_data,
            "Software Engineer",
            "Looking for Python developer...",
            "TechCorp",
            "A leading tech company",
            False
        )

        assert "<p>" in result
        assert "</p>" in result
        # Should have 3 paragraphs
        assert result.count("<p>") == 3
        assert result.count("</p>") == 3

    def test_paragraphs_contain_response_content(self, mocker, resume_data, cover_letter_response):
        """Should include all response paragraphs in output."""
        mock_call = mocker.patch("app.cover_engine.call_openai_json")
        mock_call.return_value = cover_letter_response

        result = generate_cover_letter(
            resume_data,
            "Software Engineer",
            "Looking for Python developer...",
            "TechCorp",
            "A leading tech company",
            False
        )

        for paragraph in cover_letter_response["cover_letter_body"]:
            assert paragraph in result

    def test_uses_temperature_0_7(self, mocker, resume_data, cover_letter_response):
        """Should use temperature=0.7 for creative writing."""
        mock_call = mocker.patch("app.cover_engine.call_openai_json")
        mock_call.return_value = cover_letter_response

        generate_cover_letter(
            resume_data,
            "Software Engineer",
            "Looking for Python developer...",
            "TechCorp",
            "A leading tech company",
            False
        )

        call_args = mock_call.call_args
        assert call_args.kwargs.get("temperature") == 0.7

    def test_combines_all_resume_sections(self, mocker, resume_data, cover_letter_response):
        """Should pass all resume sections as bullets to the prompt."""
        mock_call = mocker.patch("app.cover_engine.call_openai_json")
        mock_call.return_value = cover_letter_response

        generate_cover_letter(
            resume_data,
            "Software Engineer",
            "Looking for Python developer...",
            "TechCorp",
            "A leading tech company",
            False
        )

        # Check that the prompt contains bullets from all sections
        call_args = mock_call.call_args
        messages = call_args[0][0]
        content = str(messages)

        # Should include bullets from all sections
        for bullet in resume_data["spins"]:
            assert bullet in content
        for bullet in resume_data["programmer"]:
            assert bullet in content
        for bullet in resume_data["analyst"]:
            assert bullet in content

    def test_includes_summary_in_prompt(self, mocker, resume_data, cover_letter_response):
        """Should include professional summary in the prompt."""
        mock_call = mocker.patch("app.cover_engine.call_openai_json")
        mock_call.return_value = cover_letter_response

        generate_cover_letter(
            resume_data,
            "Software Engineer",
            "Looking for Python developer...",
            "TechCorp",
            "A leading tech company",
            False
        )

        call_args = mock_call.call_args
        messages = call_args[0][0]
        content = str(messages)

        assert resume_data["summary"] in content

    def test_includes_job_title_in_prompt(self, mocker, resume_data, cover_letter_response):
        """Should include job title in the prompt."""
        mock_call = mocker.patch("app.cover_engine.call_openai_json")
        mock_call.return_value = cover_letter_response

        job_title = "Senior Software Engineer"
        generate_cover_letter(
            resume_data,
            job_title,
            "Looking for Python developer...",
            "TechCorp",
            "A leading tech company",
            False
        )

        call_args = mock_call.call_args
        messages = call_args[0][0]
        content = str(messages)

        assert job_title in content

    def test_includes_company_info_in_prompt(self, mocker, resume_data, cover_letter_response):
        """Should include company info in the prompt."""
        mock_call = mocker.patch("app.cover_engine.call_openai_json")
        mock_call.return_value = cover_letter_response

        company_name = "Acme Corp"
        company_info = "A revolutionary tech startup focused on AI solutions"

        generate_cover_letter(
            resume_data,
            "Software Engineer",
            "Looking for Python developer...",
            company_name,
            company_info,
            False
        )

        call_args = mock_call.call_args
        messages = call_args[0][0]
        content = str(messages)

        assert company_name in content
        assert company_info in content

    def test_job_change_true_passed_to_prompt(self, mocker, resume_data, cover_letter_response):
        """Should pass job_change=True to the prompt."""
        mock_call = mocker.patch("app.cover_engine.call_openai_json")
        mock_call.return_value = cover_letter_response

        generate_cover_letter(
            resume_data,
            "Software Engineer",
            "Looking for Python developer...",
            "TechCorp",
            "A leading tech company",
            True  # job_change=True
        )

        call_args = mock_call.call_args
        messages = call_args[0][0]
        content = str(messages)

        assert "True" in content

    def test_job_change_false_passed_to_prompt(self, mocker, resume_data, cover_letter_response):
        """Should pass job_change=False to the prompt."""
        mock_call = mocker.patch("app.cover_engine.call_openai_json")
        mock_call.return_value = cover_letter_response

        generate_cover_letter(
            resume_data,
            "Software Engineer",
            "Looking for Python developer...",
            "TechCorp",
            "A leading tech company",
            False  # job_change=False
        )

        call_args = mock_call.call_args
        messages = call_args[0][0]
        content = str(messages)

        assert "False" in content

    def test_handles_empty_analyst_section(self, mocker, cover_letter_response):
        """Should handle resume data with empty analyst section."""
        resume_data = {
            "summary": "Test summary",
            "spins": ["Bullet 1"],
            "programmer": ["Bullet 2"],
            "analyst": []  # Empty
        }

        mock_call = mocker.patch("app.cover_engine.call_openai_json")
        mock_call.return_value = cover_letter_response

        result = generate_cover_letter(
            resume_data,
            "Software Engineer",
            "Job desc",
            "Company",
            "Info",
            False
        )

        # Should still work
        assert "<p>" in result

    def test_output_format_structure(self, mocker, resume_data, cover_letter_response):
        """Should produce correct paragraph structure."""
        mock_call = mocker.patch("app.cover_engine.call_openai_json")
        mock_call.return_value = cover_letter_response

        result = generate_cover_letter(
            resume_data,
            "Software Engineer",
            "Looking for Python developer...",
            "TechCorp",
            "A leading tech company",
            False
        )

        # Should start with <p> and end with </p>
        assert result.startswith("<p>")
        assert result.endswith("</p>")

        # Paragraphs should be joined with </p><p>
        assert "</p><p>" in result
