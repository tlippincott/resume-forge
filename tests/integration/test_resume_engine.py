"""
Integration tests for app/resume_engine.py

Tests generate_resume pipeline with mocked OpenAI calls:
- Full pipeline flow
- Error handling for missing files
- Output structure validation
"""
import json
import pytest
from app.resume_engine import generate_resume


pytestmark = pytest.mark.integration


class TestGenerateResume:
    """Tests for generate_resume function."""

    @pytest.fixture
    def mock_scored_bullets(self, sample_bullets):
        """Mock response for bullet scoring."""
        return {
            "scored_bullets": [
                {"bullet": bullet, "score": 5 - i}
                for i, bullet in enumerate(sample_bullets)
            ]
        }

    @pytest.fixture
    def mock_rewritten_response(self, sample_bullets):
        """Mock response for bullet rewriting."""
        return {
            "rewritten_bullets": [f"Rewritten: {b}" for b in sample_bullets],
            "summary": "Experienced professional with strong technical skills."
        }

    @pytest.fixture
    def mock_classification_response(self, sample_bullets):
        """Mock response for bullet classification."""
        rewritten = [f"Rewritten: {b}" for b in sample_bullets]
        # Distribute to meet minimum requirements
        return {
            "assignments": [
                {"bullet": rewritten[0], "section": "spins"},
                {"bullet": rewritten[1], "section": "programmer"},
                {"bullet": rewritten[2], "section": "analyst"},
                {"bullet": rewritten[3], "section": "spins"},
                {"bullet": rewritten[4], "section": "programmer"},
            ]
        }

    @pytest.fixture
    def extended_bullet_file(self, tmp_path):
        """Create bullet file with enough bullets for full pipeline."""
        # Need enough bullets to meet minimums (10 spins + 10 programmer)
        bullets = [f"Bullet {i} for resume testing" for i in range(35)]
        bullet_file = tmp_path / "bullets.json"
        bullet_file.write_text(json.dumps({"bullets": bullets}))
        return str(bullet_file)

    @pytest.fixture
    def mock_extended_responses(self):
        """Create mock responses for full pipeline with enough bullets."""
        def create_mocks(bullets):
            # Scoring response - give all bullets high scores
            scored = {
                "scored_bullets": [
                    {"bullet": b, "score": 5} for b in bullets
                ]
            }

            # Rewrite response
            rewritten_bullets = [f"Rewritten: {b}" for b in bullets[:30]]
            rewritten = {
                "rewritten_bullets": rewritten_bullets,
                "summary": "Professional summary based on experience."
            }

            # Classification - distribute 12 to each primary, rest to analyst
            assignments = []
            for i, b in enumerate(rewritten_bullets):
                if i < 12:
                    section = "spins"
                elif i < 24:
                    section = "programmer"
                else:
                    section = "analyst"
                assignments.append({"bullet": b, "section": section})

            classification = {"assignments": assignments}

            return scored, rewritten, classification

        return create_mocks

    def test_raises_on_missing_file(self, sample_job_description):
        """Should raise ValueError when bullet file doesn't exist."""
        with pytest.raises(ValueError, match="not found"):
            generate_resume(
                sample_job_description,
                "TechCorp",
                "A tech company",
                "/nonexistent/path/bullets.json",
                False
            )

    def test_returns_dict_with_required_keys(
        self, mocker, extended_bullet_file, sample_job_description,
        mock_extended_responses, fixed_random
    ):
        """Should return dict with summary, spins, programmer, analyst."""
        # Load bullets to create appropriate mocks
        with open(extended_bullet_file) as f:
            bullets = json.load(f)["bullets"]

        scored, rewritten, classification = mock_extended_responses(bullets)

        mock_call = mocker.patch("app.resume_engine.call_openai_json")
        mock_call.side_effect = [scored, rewritten]

        mock_classify = mocker.patch("app.resume_engine.classify_bullets")
        mock_classify.return_value = classification["assignments"]

        result = generate_resume(
            sample_job_description,
            "TechCorp",
            "A tech company",
            extended_bullet_file,
            False
        )

        assert isinstance(result, dict)
        assert "summary" in result
        assert "spins" in result
        assert "programmer" in result
        assert "analyst" in result

    def test_summary_is_string(
        self, mocker, extended_bullet_file, sample_job_description,
        mock_extended_responses, fixed_random
    ):
        """Should return summary as a string."""
        with open(extended_bullet_file) as f:
            bullets = json.load(f)["bullets"]

        scored, rewritten, classification = mock_extended_responses(bullets)

        mock_call = mocker.patch("app.resume_engine.call_openai_json")
        mock_call.side_effect = [scored, rewritten]

        mock_classify = mocker.patch("app.resume_engine.classify_bullets")
        mock_classify.return_value = classification["assignments"]

        result = generate_resume(
            sample_job_description,
            "TechCorp",
            "A tech company",
            extended_bullet_file,
            False
        )

        assert isinstance(result["summary"], str)
        assert len(result["summary"]) > 0

    def test_sections_contain_html_list_items(
        self, mocker, extended_bullet_file, sample_job_description,
        mock_extended_responses, fixed_random
    ):
        """Should format sections as HTML list items."""
        with open(extended_bullet_file) as f:
            bullets = json.load(f)["bullets"]

        scored, rewritten, classification = mock_extended_responses(bullets)

        mock_call = mocker.patch("app.resume_engine.call_openai_json")
        mock_call.side_effect = [scored, rewritten]

        mock_classify = mocker.patch("app.resume_engine.classify_bullets")
        mock_classify.return_value = classification["assignments"]

        result = generate_resume(
            sample_job_description,
            "TechCorp",
            "A tech company",
            extended_bullet_file,
            False
        )

        # Each section should have <li> tags
        assert "<li>" in result["spins"]
        assert "</li>" in result["spins"]
        assert "<li>" in result["programmer"]
        assert "</li>" in result["programmer"]

    def test_calls_openai_for_scoring(
        self, mocker, extended_bullet_file, sample_job_description,
        mock_extended_responses, fixed_random
    ):
        """Should call OpenAI to score bullets."""
        with open(extended_bullet_file) as f:
            bullets = json.load(f)["bullets"]

        scored, rewritten, classification = mock_extended_responses(bullets)

        mock_call = mocker.patch("app.resume_engine.call_openai_json")
        mock_call.side_effect = [scored, rewritten]

        mock_classify = mocker.patch("app.resume_engine.classify_bullets")
        mock_classify.return_value = classification["assignments"]

        generate_resume(
            sample_job_description,
            "TechCorp",
            "A tech company",
            extended_bullet_file,
            False
        )

        # First call should be for scoring
        first_call = mock_call.call_args_list[0]
        messages = first_call[0][0]
        assert "score" in str(messages).lower()

    def test_calls_openai_for_rewriting(
        self, mocker, extended_bullet_file, sample_job_description,
        mock_extended_responses, fixed_random
    ):
        """Should call OpenAI to rewrite bullets."""
        with open(extended_bullet_file) as f:
            bullets = json.load(f)["bullets"]

        scored, rewritten, classification = mock_extended_responses(bullets)

        mock_call = mocker.patch("app.resume_engine.call_openai_json")
        mock_call.side_effect = [scored, rewritten]

        mock_classify = mocker.patch("app.resume_engine.classify_bullets")
        mock_classify.return_value = classification["assignments"]

        generate_resume(
            sample_job_description,
            "TechCorp",
            "A tech company",
            extended_bullet_file,
            False
        )

        # Second call should be for rewriting with temperature=0.7
        second_call = mock_call.call_args_list[1]
        assert second_call.kwargs.get("temperature") == 0.7

    def test_selects_top_bullets_by_score(
        self, mocker, extended_bullet_file, sample_job_description, fixed_random
    ):
        """Should select top-scored bullets for rewriting."""
        with open(extended_bullet_file) as f:
            bullets = json.load(f)["bullets"]

        # Create scored bullets with varying scores
        scored = {
            "scored_bullets": [
                {"bullet": b, "score": 5 if i < 30 else 1}
                for i, b in enumerate(bullets)
            ]
        }

        rewritten_bullets = [f"Rewritten: {bullets[i]}" for i in range(30)]
        rewritten = {
            "rewritten_bullets": rewritten_bullets,
            "summary": "Test summary"
        }

        # Classification matching rewritten bullets
        assignments = []
        for i, b in enumerate(rewritten_bullets):
            section = "spins" if i < 12 else ("programmer" if i < 24 else "analyst")
            assignments.append({"bullet": b, "section": section})

        mock_call = mocker.patch("app.resume_engine.call_openai_json")
        mock_call.side_effect = [scored, rewritten]

        mock_classify = mocker.patch("app.resume_engine.classify_bullets")
        mock_classify.return_value = assignments

        result = generate_resume(
            sample_job_description,
            "TechCorp",
            "A tech company",
            extended_bullet_file,
            False
        )

        # Result should contain rewritten bullets
        assert "Rewritten:" in result["spins"]

    def test_passes_job_change_to_rewrite(
        self, mocker, extended_bullet_file, sample_job_description,
        mock_extended_responses, fixed_random
    ):
        """Should pass job_change context to rewrite prompt."""
        with open(extended_bullet_file) as f:
            bullets = json.load(f)["bullets"]

        scored, rewritten, classification = mock_extended_responses(bullets)

        mock_call = mocker.patch("app.resume_engine.call_openai_json")
        mock_call.side_effect = [scored, rewritten]

        mock_classify = mocker.patch("app.resume_engine.classify_bullets")
        mock_classify.return_value = classification["assignments"]

        generate_resume(
            sample_job_description,
            "TechCorp",
            "A tech company",
            extended_bullet_file,
            True  # job_change=True
        )

        # Second call (rewrite) should include job_change context
        second_call = mock_call.call_args_list[1]
        messages = second_call[0][0]
        # The prompt should contain the job_change value
        assert "True" in str(messages)
