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
from app.exceptions import FileOperationError, ValidationError


pytestmark = pytest.mark.integration


def make_bullet_item(text, section):
    return {"text": text, "section": section}


class TestGenerateResume:
    """Tests for generate_resume function."""

    @pytest.fixture
    def extended_bullet_file(self, tmp_path):
        """Create bullet file with enough bullets for full pipeline (new format)."""
        bullets = []
        for i in range(15):
            bullets.append(make_bullet_item(f"Spins bullet {i}", "spins"))
        for i in range(15):
            bullets.append(make_bullet_item(f"Programmer bullet {i}", "programmer"))
        for i in range(12):
            bullets.append(make_bullet_item(f"Analyst bullet {i}", "analyst"))
        bullet_file = tmp_path / "bullets.json"
        bullet_file.write_text(json.dumps({
            "role": "Help Desk",
            "bullets": bullets
        }))
        return str(bullet_file)

    @pytest.fixture
    def mock_responses(self, extended_bullet_file):
        """Create mock LLM responses for the full pipeline."""
        with open(extended_bullet_file) as f:
            data = json.load(f)
        bullet_items = data["bullets"]
        all_texts = [b["text"] for b in bullet_items]

        scored = {
            "scored_bullets": [
                {"bullet": text, "score": 5} for text in all_texts
            ]
        }

        # select_bullets_by_section selects 12+12+10=34 bullets
        total = 12 + 12 + 10
        rewritten = {
            "rewritten_bullets": [f"Rewritten bullet {i}" for i in range(total)],
            "summary": "Professional summary based on experience."
        }

        return scored, rewritten

    def test_raises_on_missing_file(self, sample_job_description):
        """Should raise FileOperationError when bullet file doesn't exist."""
        with pytest.raises(FileOperationError, match="not found"):
            generate_resume(
                sample_job_description,
                "TechCorp",
                "A tech company",
                "/nonexistent/path/bullets.json",
                False
            )

    def test_raises_on_invalid_bullet_library_format(self, tmp_path, sample_job_description):
        """Should raise ValidationError when bullet file uses legacy string format."""
        bullet_file = tmp_path / "legacy.json"
        bullet_file.write_text(json.dumps({
            "role": "Test",
            "bullets": ["plain string bullet"]
        }))

        with pytest.raises(ValidationError, match="validation failed"):
            generate_resume(
                sample_job_description,
                "TechCorp",
                "A tech company",
                str(bullet_file),
                False
            )

    def test_returns_dict_with_required_keys(
        self, mocker, extended_bullet_file, sample_job_description, mock_responses
    ):
        """Should return dict with summary, spins, programmer, analyst."""
        scored, rewritten = mock_responses

        mock_call = mocker.patch("app.resume_engine.call_openai_json")
        mock_call.side_effect = [scored, rewritten]

        # Mock analysis calls to avoid LLM calls
        mocker.patch("app.resume_engine.get_cached_jd_analysis", return_value={
            "required_skills": [], "preferred_skills": [], "all_keywords": [], "job_categories": []
        })
        mocker.patch("app.resume_engine.analyze_bullets", return_value=[
            {"bullet_id": f"bullet_{i:04d}", "text": f"Rewritten bullet {i}",
             "keywords": [], "category": "general", "has_impact": False}
            for i in range(34)
        ])
        mocker.patch("app.resume_engine.score_bullets_against_jd", side_effect=lambda b, _: b)

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
        self, mocker, extended_bullet_file, sample_job_description, mock_responses
    ):
        """Should return summary as a string."""
        scored, rewritten = mock_responses

        mock_call = mocker.patch("app.resume_engine.call_openai_json")
        mock_call.side_effect = [scored, rewritten]

        mocker.patch("app.resume_engine.get_cached_jd_analysis", return_value={
            "required_skills": [], "preferred_skills": [], "all_keywords": [], "job_categories": []
        })
        mocker.patch("app.resume_engine.analyze_bullets", return_value=[
            {"bullet_id": f"bullet_{i:04d}", "text": f"Rewritten bullet {i}",
             "keywords": [], "category": "general", "has_impact": False}
            for i in range(34)
        ])
        mocker.patch("app.resume_engine.score_bullets_against_jd", side_effect=lambda b, _: b)

        result = generate_resume(
            sample_job_description,
            "TechCorp",
            "A tech company",
            extended_bullet_file,
            False
        )

        assert isinstance(result["summary"], str)
        assert len(result["summary"]) > 0

    def test_sections_contain_lists(
        self, mocker, extended_bullet_file, sample_job_description, mock_responses
    ):
        """Should return sections as plain lists."""
        scored, rewritten = mock_responses

        mock_call = mocker.patch("app.resume_engine.call_openai_json")
        mock_call.side_effect = [scored, rewritten]

        mocker.patch("app.resume_engine.get_cached_jd_analysis", return_value={
            "required_skills": [], "preferred_skills": [], "all_keywords": [], "job_categories": []
        })
        mocker.patch("app.resume_engine.analyze_bullets", return_value=[
            {"bullet_id": f"bullet_{i:04d}", "text": f"Rewritten bullet {i}",
             "keywords": [], "category": "general", "has_impact": False}
            for i in range(34)
        ])
        mocker.patch("app.resume_engine.score_bullets_against_jd", side_effect=lambda b, _: b)

        result = generate_resume(
            sample_job_description,
            "TechCorp",
            "A tech company",
            extended_bullet_file,
            False
        )

        assert isinstance(result["spins"], list)
        assert isinstance(result["programmer"], list)
        assert isinstance(result["analyst"], list)
        assert len(result["spins"]) > 0
        assert len(result["programmer"]) > 0
        assert len(result["analyst"]) > 0

    def test_calls_openai_for_scoring(
        self, mocker, extended_bullet_file, sample_job_description, mock_responses
    ):
        """Should call OpenAI to score bullets."""
        scored, rewritten = mock_responses

        mock_call = mocker.patch("app.resume_engine.call_openai_json")
        mock_call.side_effect = [scored, rewritten]

        mocker.patch("app.resume_engine.get_cached_jd_analysis", return_value={
            "required_skills": [], "preferred_skills": [], "all_keywords": [], "job_categories": []
        })
        mocker.patch("app.resume_engine.analyze_bullets", return_value=[
            {"bullet_id": f"bullet_{i:04d}", "text": f"Rewritten bullet {i}",
             "keywords": [], "category": "general", "has_impact": False}
            for i in range(34)
        ])
        mocker.patch("app.resume_engine.score_bullets_against_jd", side_effect=lambda b, _: b)

        generate_resume(
            sample_job_description,
            "TechCorp",
            "A tech company",
            extended_bullet_file,
            False
        )

        first_call = mock_call.call_args_list[0]
        messages = first_call[0][0]
        assert "score" in str(messages).lower()

    def test_calls_openai_for_rewriting(
        self, mocker, extended_bullet_file, sample_job_description, mock_responses
    ):
        """Should call OpenAI to rewrite bullets with creative temperature."""
        scored, rewritten = mock_responses

        mock_call = mocker.patch("app.resume_engine.call_openai_json")
        mock_call.side_effect = [scored, rewritten]

        mocker.patch("app.resume_engine.get_cached_jd_analysis", return_value={
            "required_skills": [], "preferred_skills": [], "all_keywords": [], "job_categories": []
        })
        mocker.patch("app.resume_engine.analyze_bullets", return_value=[
            {"bullet_id": f"bullet_{i:04d}", "text": f"Rewritten bullet {i}",
             "keywords": [], "category": "general", "has_impact": False}
            for i in range(34)
        ])
        mocker.patch("app.resume_engine.score_bullets_against_jd", side_effect=lambda b, _: b)

        generate_resume(
            sample_job_description,
            "TechCorp",
            "A tech company",
            extended_bullet_file,
            False
        )

        second_call = mock_call.call_args_list[1]
        assert second_call.kwargs.get("temperature") == 0.7

    def test_extracts_role_from_bullet_file(
        self, mocker, tmp_path, sample_job_description
    ):
        """Should extract role from bullet file and pass to rewrite_prompt."""
        bullets = []
        for i in range(15):
            bullets.append(make_bullet_item(f"Spins bullet {i}", "spins"))
        for i in range(15):
            bullets.append(make_bullet_item(f"Programmer bullet {i}", "programmer"))
        for i in range(12):
            bullets.append(make_bullet_item(f"Analyst bullet {i}", "analyst"))

        bullet_file = tmp_path / "bullets_with_role.json"
        bullet_file.write_text(json.dumps({"role": "Programmer", "bullets": bullets}))

        all_texts = [b["text"] for b in bullets]
        scored = {"scored_bullets": [{"bullet": t, "score": 5} for t in all_texts]}
        rewritten = {
            "rewritten_bullets": [f"Rewritten {i}" for i in range(34)],
            "summary": "Test summary"
        }

        mock_call = mocker.patch("app.resume_engine.call_openai_json")
        mock_call.side_effect = [scored, rewritten]

        mocker.patch("app.resume_engine.get_cached_jd_analysis", return_value={
            "required_skills": [], "preferred_skills": [], "all_keywords": [], "job_categories": []
        })
        mocker.patch("app.resume_engine.analyze_bullets", return_value=[
            {"bullet_id": f"bullet_{i:04d}", "text": f"Rewritten {i}",
             "keywords": [], "category": "general", "has_impact": False}
            for i in range(34)
        ])
        mocker.patch("app.resume_engine.score_bullets_against_jd", side_effect=lambda b, _: b)

        mock_rewrite = mocker.patch("app.resume_engine.rewrite_prompt")
        mock_rewrite.return_value = [{"role": "user", "content": "test"}]

        generate_resume(
            sample_job_description,
            "TechCorp",
            "A tech company",
            str(bullet_file),
            False
        )

        assert mock_rewrite.called
        call_args = mock_rewrite.call_args
        assert call_args[0][5] == "Programmer"

    def test_defaults_to_general_when_role_missing(
        self, mocker, tmp_path, sample_job_description
    ):
        """Should default to 'General' role when role field is missing."""
        bullets = []
        for i in range(15):
            bullets.append(make_bullet_item(f"Spins bullet {i}", "spins"))
        for i in range(15):
            bullets.append(make_bullet_item(f"Programmer bullet {i}", "programmer"))
        for i in range(12):
            bullets.append(make_bullet_item(f"Analyst bullet {i}", "analyst"))

        bullet_file = tmp_path / "bullets_no_role.json"
        bullet_file.write_text(json.dumps({"bullets": bullets}))

        all_texts = [b["text"] for b in bullets]
        scored = {"scored_bullets": [{"bullet": t, "score": 5} for t in all_texts]}
        rewritten = {
            "rewritten_bullets": [f"Rewritten {i}" for i in range(34)],
            "summary": "Test summary"
        }

        mock_call = mocker.patch("app.resume_engine.call_openai_json")
        mock_call.side_effect = [scored, rewritten]

        mocker.patch("app.resume_engine.get_cached_jd_analysis", return_value={
            "required_skills": [], "preferred_skills": [], "all_keywords": [], "job_categories": []
        })
        mocker.patch("app.resume_engine.analyze_bullets", return_value=[
            {"bullet_id": f"bullet_{i:04d}", "text": f"Rewritten {i}",
             "keywords": [], "category": "general", "has_impact": False}
            for i in range(34)
        ])
        mocker.patch("app.resume_engine.score_bullets_against_jd", side_effect=lambda b, _: b)

        mock_rewrite = mocker.patch("app.resume_engine.rewrite_prompt")
        mock_rewrite.return_value = [{"role": "user", "content": "test"}]

        generate_resume(
            sample_job_description,
            "TechCorp",
            "A tech company",
            str(bullet_file),
            False
        )

        call_args = mock_rewrite.call_args
        assert call_args[0][5] == "General"
