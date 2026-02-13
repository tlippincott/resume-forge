import json
import time
from openai import OpenAI
from openai import APIError, APITimeoutError, RateLimitError, APIConnectionError
from app.config import API_KEY, MODEL_NAME

client = OpenAI(api_key=API_KEY)

# Timeout and retry configuration
DEFAULT_TIMEOUT = 60  # seconds
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 2  # seconds
MAX_RETRY_DELAY = 32  # seconds (cap for exponential backoff)


def call_openai_json(messages, temperature=0.0, timeout=None):
    """
    Call OpenAI API with JSON response format, timeout, and comprehensive error handling.

    Args:
        messages: List of message dicts for the chat completion
        temperature: Temperature parameter for response randomness (0.0-2.0)
        timeout: Request timeout in seconds (default: 60s)

    Returns:
        Parsed JSON response from the API

    Raises:
        RuntimeError: On JSON parse failure, auth errors, or max retries exceeded
    """
    if timeout is None:
        timeout = DEFAULT_TIMEOUT

    retry_delay = INITIAL_RETRY_DELAY

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "Return ONLY valid JSON."},
                    *messages
                ],
                temperature=temperature,
                timeout=timeout
            )

            if not response.choices:
                raise RuntimeError("OpenAI returned empty response")

            return json.loads(response.choices[0].message.content)

        except json.JSONDecodeError as e:
            # Retry on JSON parse failures (malformed API response)
            if attempt == MAX_RETRIES:
                raise RuntimeError(
                    f"JSON parse failure after {MAX_RETRIES + 1} attempts: {e}"
                )
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, MAX_RETRY_DELAY)

        except RateLimitError as e:
            # Retry on rate limits with exponential backoff
            if attempt == MAX_RETRIES:
                raise RuntimeError(
                    f"Rate limit exceeded after {MAX_RETRIES + 1} attempts. "
                    f"Please wait before retrying. Error: {e}"
                )
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, MAX_RETRY_DELAY)

        except APITimeoutError as e:
            # Retry on timeouts
            if attempt == MAX_RETRIES:
                raise RuntimeError(
                    f"API request timed out after {MAX_RETRIES + 1} attempts "
                    f"(timeout: {timeout}s). Error: {e}"
                )
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, MAX_RETRY_DELAY)

        except APIConnectionError as e:
            # Retry on connection errors
            if attempt == MAX_RETRIES:
                raise RuntimeError(
                    f"API connection failed after {MAX_RETRIES + 1} attempts. "
                    f"Check your internet connection. Error: {e}"
                )
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, MAX_RETRY_DELAY)

        except APIError as e:
            # Don't retry on API errors (auth, invalid request, etc.)
            raise RuntimeError(
                f"OpenAI API error (attempt {attempt + 1}/{MAX_RETRIES + 1}): {e}"
            )

        except (KeyError, AttributeError) as e:
            # Retry on unexpected response structure
            if attempt == MAX_RETRIES:
                raise RuntimeError(
                    f"Unexpected API response structure after {MAX_RETRIES + 1} attempts: {e}"
                )
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, MAX_RETRY_DELAY)
