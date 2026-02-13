import json
import time
from openai import OpenAI
from openai import APIError, APITimeoutError, RateLimitError, APIConnectionError
from app.config import config
from app.exceptions import LLMServiceError
from app.logging_config import get_logger

# Initialize OpenAI client with configuration
client = OpenAI(
    api_key=config.api.api_key,
    base_url=config.api.base_url  # None by default, can be overridden for custom endpoints
)
logger = get_logger(__name__)


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
        LLMServiceError: On JSON parse failure, auth errors, or max retries exceeded
    """
    logger.debug(f"Calling OpenAI API with {len(messages)} messages, temperature={temperature}, timeout={timeout}s")
    if timeout is None:
        timeout = config.api.default_timeout

    retry_delay = config.api.initial_retry_delay

    for attempt in range(config.api.max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=config.api.model_name,
                messages=[
                    {"role": "system", "content": "Return ONLY valid JSON."},
                    *messages
                ],
                temperature=temperature,
                timeout=timeout
            )

            if not response.choices:
                logger.error("OpenAI returned empty response")
                raise LLMServiceError("OpenAI returned empty response")

            result = json.loads(response.choices[0].message.content)
            logger.debug(f"OpenAI API call successful on attempt {attempt + 1}")
            return result

        except json.JSONDecodeError as e:
            # Retry on JSON parse failures (malformed API response)
            logger.warning(f"JSON parse failure on attempt {attempt + 1}: {e}")
            if attempt == config.api.max_retries:
                logger.error(f"JSON parse failure after {config.api.max_retries + 1} attempts: {e}")
                raise LLMServiceError(
                    f"JSON parse failure after {config.api.max_retries + 1} attempts: {e}"
                )
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, config.api.max_retry_delay)

        except RateLimitError as e:
            # Retry on rate limits with exponential backoff
            logger.warning(f"Rate limit exceeded on attempt {attempt + 1}, retrying with {retry_delay}s delay")
            if attempt == config.api.max_retries:
                logger.error(f"Rate limit exceeded after {config.api.max_retries + 1} attempts: {e}")
                raise LLMServiceError(
                    f"Rate limit exceeded after {config.api.max_retries + 1} attempts. "
                    f"Please wait before retrying. Error: {e}"
                )
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, config.api.max_retry_delay)

        except APITimeoutError as e:
            # Retry on timeouts
            logger.warning(f"API timeout on attempt {attempt + 1} (timeout: {timeout}s)")
            if attempt == config.api.max_retries:
                logger.error(f"API request timed out after {config.api.max_retries + 1} attempts (timeout: {timeout}s): {e}")
                raise LLMServiceError(
                    f"API request timed out after {config.api.max_retries + 1} attempts "
                    f"(timeout: {timeout}s). Error: {e}"
                )
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, config.api.max_retry_delay)

        except APIConnectionError as e:
            # Retry on connection errors
            logger.warning(f"API connection error on attempt {attempt + 1}")
            if attempt == config.api.max_retries:
                logger.error(f"API connection failed after {config.api.max_retries + 1} attempts: {e}")
                raise LLMServiceError(
                    f"API connection failed after {config.api.max_retries + 1} attempts. "
                    f"Check your internet connection. Error: {e}"
                )
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, config.api.max_retry_delay)

        except APIError as e:
            # Don't retry on API errors (auth, invalid request, etc.)
            logger.error(f"OpenAI API error (attempt {attempt + 1}/{config.api.max_retries + 1}): {e}")
            raise LLMServiceError(
                f"OpenAI API error (attempt {attempt + 1}/{config.api.max_retries + 1}): {e}"
            )

        except (KeyError, AttributeError) as e:
            # Retry on unexpected response structure
            logger.warning(f"Unexpected API response structure on attempt {attempt + 1}: {e}")
            if attempt == config.api.max_retries:
                logger.error(f"Unexpected API response structure after {config.api.max_retries + 1} attempts: {e}")
                raise LLMServiceError(
                    f"Unexpected API response structure after {config.api.max_retries + 1} attempts: {e}"
                )
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, config.api.max_retry_delay)
