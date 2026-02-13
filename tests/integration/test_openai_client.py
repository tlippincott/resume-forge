"""
Integration tests for app/openai_client.py

Tests call_openai_json with mocked OpenAI client:
- Successful JSON parsing
- Retry logic on decode errors
- Error handling
- Timeout configuration
- Rate limiting and exponential backoff
"""
import json
import pytest
from unittest.mock import MagicMock
from openai import APIError, APITimeoutError, RateLimitError, APIConnectionError
from app.openai_client import call_openai_json, DEFAULT_TIMEOUT, MAX_RETRIES
from app.exceptions import LLMServiceError


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
        """Should raise LLMServiceError after exhausting MAX_RETRIES."""
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

        with pytest.raises(LLMServiceError, match="JSON parse failure"):
            call_openai_json(sample_messages)

        # Should have tried MAX_RETRIES + 1 times (4 total: initial + 3 retries)
        assert mock_client.chat.completions.create.call_count == MAX_RETRIES + 1

    def test_raises_on_empty_choices(self, mocker, sample_messages):
        """Should raise LLMServiceError when response has empty choices."""
        mock_response = MagicMock()
        mock_response.choices = []

        mock_client = mocker.patch("app.openai_client.client")
        mock_client.chat.completions.create.return_value = mock_response

        with pytest.raises(LLMServiceError, match="empty response"):
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

    def test_max_retries_constant(self, mocker, sample_messages):
        """Should use MAX_RETRIES constant for retry attempts."""
        mock_message = MagicMock()
        mock_message.content = "invalid"

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = mocker.patch("app.openai_client.client")
        mock_client.chat.completions.create.return_value = mock_response

        mocker.patch("app.openai_client.time.sleep")

        with pytest.raises(LLMServiceError):
            call_openai_json(sample_messages)

        # Should have tried MAX_RETRIES + 1 times (initial + retries)
        assert mock_client.chat.completions.create.call_count == MAX_RETRIES + 1

    # ========== NEW: Timeout Tests ==========

    def test_uses_custom_timeout(self, mocker, mock_openai_response, sample_messages):
        """Should pass custom timeout to OpenAI API."""
        mock_response = mock_openai_response({"result": "test"})
        mock_client = mocker.patch("app.openai_client.client")
        mock_client.chat.completions.create.return_value = mock_response

        call_openai_json(sample_messages, timeout=120)

        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["timeout"] == 120

    def test_uses_default_timeout_when_not_specified(self, mocker, mock_openai_response, sample_messages):
        """Should use DEFAULT_TIMEOUT (60s) when timeout not specified."""
        mock_response = mock_openai_response({"result": "test"})
        mock_client = mocker.patch("app.openai_client.client")
        mock_client.chat.completions.create.return_value = mock_response

        call_openai_json(sample_messages)

        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["timeout"] == DEFAULT_TIMEOUT

    # ========== NEW: Error Handling Tests ==========

    def test_retries_on_rate_limit_error(self, mocker, mock_openai_response, sample_messages):
        """Should retry on RateLimitError with exponential backoff."""
        mock_success = mock_openai_response({"result": "success"})
        mock_client = mocker.patch("app.openai_client.client")

        # Create mock request and response for RateLimitError
        mock_request = MagicMock()
        mock_response = MagicMock()
        mock_response.request = mock_request

        # First call raises RateLimitError, second succeeds
        rate_limit_error = RateLimitError("Rate limit exceeded", response=mock_response, body=None)
        mock_client.chat.completions.create.side_effect = [
            rate_limit_error,
            mock_success
        ]

        mock_sleep = mocker.patch("app.openai_client.time.sleep")

        result = call_openai_json(sample_messages)

        assert result == {"result": "success"}
        assert mock_client.chat.completions.create.call_count == 2
        # Should have slept once (initial retry delay = 2s)
        mock_sleep.assert_called_once_with(2)

    def test_retries_on_api_timeout_error(self, mocker, mock_openai_response, sample_messages):
        """Should retry on APITimeoutError."""
        mock_success = mock_openai_response({"result": "success"})
        mock_client = mocker.patch("app.openai_client.client")

        # First call times out, second succeeds
        mock_client.chat.completions.create.side_effect = [
            APITimeoutError("Request timed out"),
            mock_success
        ]

        mock_sleep = mocker.patch("app.openai_client.time.sleep")

        result = call_openai_json(sample_messages)

        assert result == {"result": "success"}
        assert mock_client.chat.completions.create.call_count == 2
        mock_sleep.assert_called_once_with(2)

    def test_retries_on_connection_error(self, mocker, mock_openai_response, sample_messages):
        """Should retry on APIConnectionError."""
        mock_success = mock_openai_response({"result": "success"})
        mock_client = mocker.patch("app.openai_client.client")

        # Create mock request for APIConnectionError
        mock_request = MagicMock()
        # First call has connection error, second succeeds
        connection_error = APIConnectionError(message="Connection failed", request=mock_request)
        mock_client.chat.completions.create.side_effect = [
            connection_error,
            mock_success
        ]

        mock_sleep = mocker.patch("app.openai_client.time.sleep")

        result = call_openai_json(sample_messages)

        assert result == {"result": "success"}
        assert mock_client.chat.completions.create.call_count == 2
        mock_sleep.assert_called_once_with(2)

    def test_fails_immediately_on_api_error(self, mocker, sample_messages):
        """Should not retry on APIError (auth errors, invalid requests)."""
        mock_client = mocker.patch("app.openai_client.client")

        # Create mock request for APIError
        mock_request = MagicMock()
        api_error = APIError(message="Invalid API key", request=mock_request, body=None)
        mock_client.chat.completions.create.side_effect = api_error

        with pytest.raises(LLMServiceError, match="OpenAI API error"):
            call_openai_json(sample_messages)

        # Should only try once (no retries for APIError)
        assert mock_client.chat.completions.create.call_count == 1

    def test_exponential_backoff(self, mocker, mock_openai_response, sample_messages):
        """Should use exponential backoff: 2s, 4s, 8s, 16s."""
        mock_success = mock_openai_response({"result": "success"})
        mock_client = mocker.patch("app.openai_client.client")

        # Create mock request and response for RateLimitError
        mock_request = MagicMock()
        mock_response = MagicMock()
        mock_response.request = mock_request

        # First 3 calls fail, 4th succeeds
        rate_limit_error = RateLimitError("Rate limit", response=mock_response, body=None)
        mock_client.chat.completions.create.side_effect = [
            rate_limit_error,
            rate_limit_error,
            rate_limit_error,
            mock_success
        ]

        mock_sleep = mocker.patch("app.openai_client.time.sleep")

        result = call_openai_json(sample_messages)

        assert result == {"result": "success"}
        # Should have slept 3 times with exponential backoff
        assert mock_sleep.call_count == 3
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert sleep_calls == [2, 4, 8]  # Exponential: 2, 4, 8

    def test_backoff_caps_at_max_delay(self, mocker, sample_messages):
        """Should cap exponential backoff at MAX_RETRY_DELAY (32s)."""
        mock_client = mocker.patch("app.openai_client.client")

        # Create mock request and response for RateLimitError
        mock_request = MagicMock()
        mock_response = MagicMock()
        mock_response.request = mock_request

        # All calls fail to test max backoff
        rate_limit_error = RateLimitError("Rate limit", response=mock_response, body=None)
        mock_client.chat.completions.create.side_effect = rate_limit_error

        mock_sleep = mocker.patch("app.openai_client.time.sleep")

        with pytest.raises(LLMServiceError, match="Rate limit exceeded"):
            call_openai_json(sample_messages)

        # With MAX_RETRIES=3, we have 4 attempts total (initial + 3 retries)
        # We sleep after attempts 0, 1, 2 (3 sleeps): 2s, 4s, 8s
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert sleep_calls == [2, 4, 8]
        # None should exceed 32s
        assert all(delay <= 32 for delay in sleep_calls)

    def test_rate_limit_error_message_includes_context(self, mocker, sample_messages):
        """Should provide helpful error message on rate limit failure."""
        mock_client = mocker.patch("app.openai_client.client")

        # Create mock request and response for RateLimitError
        mock_request = MagicMock()
        mock_response = MagicMock()
        mock_response.request = mock_request

        rate_limit_error = RateLimitError("Rate limit", response=mock_response, body=None)
        mock_client.chat.completions.create.side_effect = rate_limit_error
        mocker.patch("app.openai_client.time.sleep")

        with pytest.raises(LLMServiceError, match=r"Rate limit exceeded after \d+ attempts"):
            call_openai_json(sample_messages)

    def test_timeout_error_message_includes_timeout_value(self, mocker, sample_messages):
        """Should include timeout value in error message."""
        mock_client = mocker.patch("app.openai_client.client")
        mock_client.chat.completions.create.side_effect = APITimeoutError("Timeout")
        mocker.patch("app.openai_client.time.sleep")

        with pytest.raises(LLMServiceError, match=r"timeout: 90s"):
            call_openai_json(sample_messages, timeout=90)

    def test_connection_error_message_suggests_network_check(self, mocker, sample_messages):
        """Should suggest checking internet connection on connection failure."""
        mock_client = mocker.patch("app.openai_client.client")

        # Create mock request for APIConnectionError
        mock_request = MagicMock()
        connection_error = APIConnectionError(message="Connection failed", request=mock_request)
        mock_client.chat.completions.create.side_effect = connection_error
        mocker.patch("app.openai_client.time.sleep")

        with pytest.raises(LLMServiceError, match="Check your internet connection"):
            call_openai_json(sample_messages)
