"""
Shared fixtures and test environment setup for Resume-Forge tests.
"""
import json
import os
import pytest
from unittest.mock import MagicMock


# ============================================================================
# Environment Setup
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def set_test_env():
    """Set required environment variables for testing."""
    os.environ.setdefault("API_KEY", "test-api-key-not-real")
    os.environ.setdefault("MODEL_NAME", "gpt-4")
    yield


# ============================================================================
# Sample Data Fixtures
# ============================================================================

@pytest.fixture
def sample_job_description():
    """Sample job description for testing."""
    return """
    Software Engineer - Python Development

    Requirements:
    - 3+ years Python experience
    - Experience with REST APIs
    - Database knowledge (PostgreSQL, MySQL)
    - Strong problem-solving skills
    """


@pytest.fixture
def sample_bullets():
    """Sample resume bullets for testing."""
    return [
        "Developed Python REST APIs serving 10K requests/day",
        "Managed PostgreSQL databases with 5TB of data",
        "Troubleshot production issues reducing downtime by 40%",
        "Collaborated with cross-functional teams on feature delivery",
        "Automated deployment pipelines using Jenkins and Docker",
    ]


@pytest.fixture
def sample_company_info():
    """Sample company information."""
    return {
        "name": "TechCorp Inc",
        "info": "A leading technology company focused on cloud solutions."
    }



# ============================================================================
# Mock OpenAI Client Fixtures
# ============================================================================

@pytest.fixture
def mock_openai_response():
    """Factory to create mock OpenAI response objects."""
    def _make(content):
        """Create a mock response with the given JSON content."""
        mock_message = MagicMock()
        mock_message.content = json.dumps(content) if isinstance(content, dict) else content

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        return mock_response

    return _make


@pytest.fixture
def mock_openai_client(mocker, mock_openai_response):
    """Mock the OpenAI client for testing."""
    mock_client = mocker.patch("app.openai_client.client")

    # Default response - can be overridden in tests
    default_response = mock_openai_response({"result": "default"})
    mock_client.chat.completions.create.return_value = default_response

    return mock_client


# ============================================================================
# Resume Data Fixtures
# ============================================================================

@pytest.fixture
def sample_resume_data():
    """Sample resume data structure returned by generate_resume."""
    return {
        "summary": "Experienced software engineer with expertise in Python and cloud technologies.",
        "spins": [
            "Resolved customer issues with quick turnaround",
            "Collaborated with product teams on feature requests",
        ],
        "programmer": [
            "Built REST APIs using Python Flask",
            "Automated CI/CD pipelines with Jenkins",
        ],
        "analyst": [
            "Performed root cause analysis on production incidents",
            "Created documentation for support processes",
        ]
    }



# ============================================================================
# Temporary File Fixtures
# ============================================================================

@pytest.fixture
def temp_bullet_file(tmp_path, sample_bullets):
    """Create a temporary bullet file for testing."""
    bullet_file = tmp_path / "bullets.json"
    bullet_file.write_text(json.dumps({"bullets": sample_bullets}))
    return str(bullet_file)
