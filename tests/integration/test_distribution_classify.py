"""
Integration tests for classify_bullets in app/distribution_engine.py

Tests the LLM-dependent classification with mocked OpenAI calls:
- Response structure validation
- Error handling for malformed responses
- Temperature setting
"""
import pytest
from app.distribution_engine import classify_bullets
from app.exceptions import ValidationError, DataProcessingError


pytestmark = pytest.mark.integration


class TestClassifyBullets:
    """Tests for classify_bullets function."""

    @pytest.fixture
    def sample_bullets(self):
        """Sample bullets for classification."""
        return [
            "Resolved customer technical issues with quick turnaround",
            "Built Python REST APIs serving production traffic",
            "Performed root cause analysis on system outages",
            "Collaborated with product teams on feature delivery",
            "Automated CI/CD pipelines using Jenkins",
        ]

    @pytest.fixture
    def valid_classification_response(self, sample_bullets):
        """Valid classification response from LLM."""
        return {
            "assignments": [
                {"bullet": sample_bullets[0], "section": "spins"},
                {"bullet": sample_bullets[1], "section": "programmer"},
                {"bullet": sample_bullets[2], "section": "analyst"},
                {"bullet": sample_bullets[3], "section": "spins"},
                {"bullet": sample_bullets[4], "section": "programmer"},
            ]
        }

    def test_returns_assignments_list(self, mocker, sample_bullets, valid_classification_response):
        """Should return list of assignment dicts."""
        mock_call = mocker.patch("app.distribution_engine.call_openai_json")
        mock_call.return_value = valid_classification_response

        result = classify_bullets(sample_bullets)

        assert isinstance(result, list)
        assert len(result) == len(sample_bullets)

    def test_assignments_have_correct_structure(
        self, mocker, sample_bullets, valid_classification_response
    ):
        """Each assignment should have bullet and section keys."""
        mock_call = mocker.patch("app.distribution_engine.call_openai_json")
        mock_call.return_value = valid_classification_response

        result = classify_bullets(sample_bullets)

        for assignment in result:
            assert "bullet" in assignment
            assert "section" in assignment
            assert assignment["section"] in {"spins", "programmer", "analyst"}

    def test_uses_temperature_zero(self, mocker, sample_bullets, valid_classification_response):
        """Should use temperature=0.0 for deterministic classification."""
        mock_call = mocker.patch("app.distribution_engine.call_openai_json")
        mock_call.return_value = valid_classification_response

        classify_bullets(sample_bullets)

        call_args = mock_call.call_args
        assert call_args.kwargs.get("temperature") == 0.0

    def test_raises_on_non_dict_response(self, mocker, sample_bullets):
        """Should raise DataProcessingError when LLM returns non-dict."""
        mock_call = mocker.patch("app.distribution_engine.call_openai_json")
        mock_call.return_value = ["not", "a", "dict"]

        with pytest.raises(DataProcessingError, match="Expected dict"):
            classify_bullets(sample_bullets)

    def test_raises_on_missing_assignments_key(self, mocker, sample_bullets):
        """Should raise DataProcessingError when response missing 'assignments' key."""
        mock_call = mocker.patch("app.distribution_engine.call_openai_json")
        mock_call.return_value = {"wrong_key": []}

        with pytest.raises(DataProcessingError, match="missing 'assignments' key"):
            classify_bullets(sample_bullets)

    def test_raises_on_invalid_assignment_structure(self, mocker, sample_bullets):
        """Should raise error on invalid assignment structure."""
        mock_call = mocker.patch("app.distribution_engine.call_openai_json")
        mock_call.return_value = {
            "assignments": [
                {"bullet": "test"}  # Missing 'section' key
            ]
        }

        with pytest.raises(ValidationError, match="missing 'section' key"):
            classify_bullets(sample_bullets)

    def test_raises_on_invalid_section_name(self, mocker, sample_bullets):
        """Should raise error when section name is invalid."""
        mock_call = mocker.patch("app.distribution_engine.call_openai_json")
        mock_call.return_value = {
            "assignments": [
                {"bullet": "test bullet", "section": "invalid_section"}
            ]
        }

        with pytest.raises(ValidationError, match="invalid section"):
            classify_bullets(sample_bullets)

    def test_raises_on_empty_assignments(self, mocker, sample_bullets):
        """Should raise error when assignments list is empty."""
        mock_call = mocker.patch("app.distribution_engine.call_openai_json")
        mock_call.return_value = {"assignments": []}

        with pytest.raises(ValidationError, match="empty"):
            classify_bullets(sample_bullets)

    def test_validates_bullet_is_string(self, mocker, sample_bullets):
        """Should raise error when bullet is not a string."""
        mock_call = mocker.patch("app.distribution_engine.call_openai_json")
        mock_call.return_value = {
            "assignments": [
                {"bullet": 123, "section": "spins"}  # bullet should be string
            ]
        }

        with pytest.raises(ValidationError, match="not string"):
            classify_bullets(sample_bullets)

    def test_validates_bullet_not_empty(self, mocker, sample_bullets):
        """Should raise error when bullet is empty string."""
        mock_call = mocker.patch("app.distribution_engine.call_openai_json")
        mock_call.return_value = {
            "assignments": [
                {"bullet": "", "section": "spins"}
            ]
        }

        with pytest.raises(ValidationError, match="empty bullet"):
            classify_bullets(sample_bullets)

    def test_passes_bullets_to_prompt(self, mocker, sample_bullets, valid_classification_response):
        """Should pass all bullets to the distribution prompt."""
        mock_call = mocker.patch("app.distribution_engine.call_openai_json")
        mock_call.return_value = valid_classification_response

        classify_bullets(sample_bullets)

        call_args = mock_call.call_args
        messages = call_args[0][0]
        content = str(messages)

        # All bullets should be in the prompt
        for bullet in sample_bullets:
            assert bullet in content

    def test_handles_all_same_section(self, mocker, sample_bullets):
        """Should handle case where all bullets go to same section."""
        response = {
            "assignments": [
                {"bullet": b, "section": "programmer"}
                for b in sample_bullets
            ]
        }

        mock_call = mocker.patch("app.distribution_engine.call_openai_json")
        mock_call.return_value = response

        result = classify_bullets(sample_bullets)

        assert all(a["section"] == "programmer" for a in result)

    def test_preserves_bullet_order(self, mocker, sample_bullets, valid_classification_response):
        """Should return assignments in same order as response."""
        mock_call = mocker.patch("app.distribution_engine.call_openai_json")
        mock_call.return_value = valid_classification_response

        result = classify_bullets(sample_bullets)

        # Order should match the response
        for i, assignment in enumerate(result):
            expected = valid_classification_response["assignments"][i]
            assert assignment["bullet"] == expected["bullet"]
            assert assignment["section"] == expected["section"]
