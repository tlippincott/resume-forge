"""
Integration tests for app/openai_client.py

Tests call_openai_json with mocked OpenAI client:
- Successful JSON parsing
- Retry logic on decode errors
- Error handling
"""
import json
import pytest
from unittest.mock import MagicMock
from app.openai_client import call_openai_json


pytestmark = pytest.mark.integration


class TestCallOpenaiJson:
    """Tests for call_openai_json function."""

    @pytest.fixture
    def sample_messages(self):
        """Sample messages for OpenAI call."""
        return [{"role": "user", "content": "Return a JSON object with key 'result'"}]

    def test_returns_parsed_json(self, mocker, mock_openai_response, sample_messages):
        """Should return parsed JSON from response."""
        expected_data = {"result": "success", "value": 42}
        mock_response = mock_openai_response(expected_data)

        mock_client = mocker.patch("app.openai_client.client")
        mock_client.chat.completions.create.return_value = mock_response

        result = call_openai_json(sample_messages)

        assert result == expected_data

    def test_uses_correct_temperature(self, mocker, mock_openai_response, sample_messages):
        """Should pass temperature to OpenAI API."""
        mock_response = mock_openai_response({"result": "test"})
        mock_client = mocker.patch("app.openai_client.client")
        mock_client.chat.completions.create.return_value = mock_response

        call_openai_json(sample_messages, temperature=0.7)

        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["temperature"] == 0.7

    def test_default_temperature_is_zero(self, mocker, mock_openai_response, sample_messages):
        """Should use temperature=0.0 by default."""
        mock_response = mock_openai_response({"result": "test"})
        mock_client = mocker.patch("app.openai_client.client")
        mock_client.chat.completions.create.return_value = mock_response

        call_openai_json(sample_messages)

        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["temperature"] == 0.0

    def test_adds_system_message(self, mocker, mock_openai_response, sample_messages):
        """Should prepend system message requesting JSON."""
        mock_response = mock_openai_response({"result": "test"})
        mock_client = mocker.patch("app.openai_client.client")
        mock_client.chat.completions.create.return_value = mock_response

        call_openai_json(sample_messages)

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]

        # First message should be system message
        assert messages[0]["role"] == "system"
        assert "JSON" in messages[0]["content"]

    def test_retries_on_json_decode_error(self, mocker, sample_messages):
        """Should retry on JSONDecodeError."""
        # First call returns invalid JSON, second returns valid
        mock_message_bad = MagicMock()
        mock_message_bad.content = "not valid json"

        mock_message_good = MagicMock()
        mock_message_good.content = '{"result": "success"}'

        mock_choice_bad = MagicMock()
        mock_choice_bad.message = mock_message_bad

        mock_choice_good = MagicMock()
        mock_choice_good.message = mock_message_good

        mock_response_bad = MagicMock()
        mock_response_bad.choices = [mock_choice_bad]

        mock_response_good = MagicMock()
        mock_response_good.choices = [mock_choice_good]

        mock_client = mocker.patch("app.openai_client.client")
        mock_client.chat.completions.create.side_effect = [
            mock_response_bad,
            mock_response_good
        ]

        # Mock time.sleep to speed up test
        mocker.patch("app.openai_client.time.sleep")

        result = call_openai_json(sample_messages)

        assert result == {"result": "success"}
        assert mock_client.chat.completions.create.call_count == 2

    def test_raises_after_max_retries(self, mocker, sample_messages):
        """Should raise RuntimeError after exhausting retries."""
        mock_message = MagicMock()
        mock_message.content = "not valid json"

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = mocker.patch("app.openai_client.client")
        mock_client.chat.completions.create.return_value = mock_response

        # Mock time.sleep to speed up test
        mocker.patch("app.openai_client.time.sleep")

        with pytest.raises(RuntimeError, match="JSON parse failure"):
            call_openai_json(sample_messages, retries=2)

        # Should have tried 3 times (initial + 2 retries)
        assert mock_client.chat.completions.create.call_count == 3

    def test_raises_on_empty_choices(self, mocker, sample_messages):
        """Should raise RuntimeError when response has empty choices."""
        mock_response = MagicMock()
        mock_response.choices = []

        mock_client = mocker.patch("app.openai_client.client")
        mock_client.chat.completions.create.return_value = mock_response

        with pytest.raises(RuntimeError, match="empty response"):
            call_openai_json(sample_messages)

    def test_handles_nested_json(self, mocker, mock_openai_response, sample_messages):
        """Should handle nested JSON structures."""
        expected_data = {
            "result": {
                "items": [{"id": 1, "name": "test"}],
                "metadata": {"count": 1}
            }
        }
        mock_response = mock_openai_response(expected_data)

        mock_client = mocker.patch("app.openai_client.client")
        mock_client.chat.completions.create.return_value = mock_response

        result = call_openai_json(sample_messages)

        assert result == expected_data

    def test_handles_array_json(self, mocker, sample_messages):
        """Should handle JSON arrays."""
        expected_data = [{"id": 1}, {"id": 2}]

        mock_message = MagicMock()
        mock_message.content = json.dumps(expected_data)

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = mocker.patch("app.openai_client.client")
        mock_client.chat.completions.create.return_value = mock_response

        result = call_openai_json(sample_messages)

        assert result == expected_data

    def test_custom_retry_count(self, mocker, sample_messages):
        """Should respect custom retry count."""
        mock_message = MagicMock()
        mock_message.content = "invalid"

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = mocker.patch("app.openai_client.client")
        mock_client.chat.completions.create.return_value = mock_response

        mocker.patch("app.openai_client.time.sleep")

        with pytest.raises(RuntimeError):
            call_openai_json(sample_messages, retries=5)

        # Should have tried 6 times (initial + 5 retries)
        assert mock_client.chat.completions.create.call_count == 6
