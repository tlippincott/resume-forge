"""Integration tests for Gradio app workflow."""

import pytest
from ui.gradio_app import handle_generate, handle_preview_update, handle_pdf_generation
from pathlib import Path


class TestGradioWorkflow:
    """Test the full workflow of the Gradio app."""

    @pytest.fixture
    def sample_inputs(self):
        """Sample inputs for testing."""
        return {
            "jd": "Looking for a software engineer with Python experience",
            "company": "Test Company",
            "info": "A leading tech company",
            "bullet_file": str(Path(__file__).parent.parent.parent / "bullet_libs" / "help_desk.json"),
            "job_change": False
        }

    def test_generate_handler_returns_correct_outputs(self, sample_inputs):
        """Test that handle_generate returns the expected number of outputs."""
        # Skip if bullet file doesn't exist
        if not Path(sample_inputs["bullet_file"]).exists():
            pytest.skip("Bullet example file not found")

        result = handle_generate(
            sample_inputs["jd"],
            "Test Job Title",
            sample_inputs["company"],
            sample_inputs["info"],
            sample_inputs["bullet_file"],
            sample_inputs["job_change"]
        )

        # Should return 22 outputs (includes metadata states, canonical bullets, role, radio choices, status, company_name)
        assert len(result) == 22

        # First output should be dict (JSON)
        assert isinstance(result[0], dict)

        # Should have summary, spins, programmer, analyst keys
        assert "summary" in result[0]
        assert "spins" in result[0]
        assert "programmer" in result[0]
        assert "analyst" in result[0]

        # Edit textbox outputs (1-4) should be strings
        for i in range(1, 5):
            assert isinstance(result[i], str)

        # State outputs (5-15)
        assert isinstance(result[5], str)  # state_summary
        assert isinstance(result[6], list)  # state_spins (with IDs)
        assert isinstance(result[7], list)  # state_programmer (with IDs)
        assert isinstance(result[8], list)  # state_analyst (with IDs)
        assert isinstance(result[9], str)  # state_job_title
        assert isinstance(result[10], str)  # state_selected_bullet_file
        assert isinstance(result[11], list)  # state_analyzed_bullets
        assert isinstance(result[12], dict)  # state_jd_analysis
        assert isinstance(result[13], set)  # state_used_bullet_ids
        assert isinstance(result[14], str)  # state_job_description
        assert isinstance(result[15], list)  # state_canonical_bullets
        assert isinstance(result[16], str)   # state_role
        # Outputs 17-19 are Gradio Radio components (bullet selection dropdowns)
        # Output 20 is a Gradio Markdown (status)
        # Output 21 is company name (str)

    def test_generate_handler_with_missing_bullet_file(self):
        """Test that handle_generate handles missing bullet file."""
        result = handle_generate(
            "Test JD",
            "Test Job Title",
            "Test Company",
            "Test Info",
            None,  # No bullet file
            False
        )

        # Should return 22 outputs with error (includes metadata states, canonical bullets, role, radio choices, status, company_name)
        assert len(result) == 22
        assert "error" in result[0]

    def test_preview_update_handler(self):
        """Test that handle_preview_update generates HTML."""
        # Create canonical bullets structure
        canonical_bullets = [
            {"text": "Bullet 1", "bullet_id": "1", "section": "spins"},
            {"text": "Bullet 2", "bullet_id": "2", "section": "spins"},
            {"text": "Prog bullet 1", "bullet_id": "3", "section": "programmer"},
            {"text": "Prog bullet 2", "bullet_id": "4", "section": "programmer"},
            {"text": "Analyst bullet 1", "bullet_id": "5", "section": "analyst"}
        ]

        html = handle_preview_update(
            "Test summary",
            canonical_bullets
        )

        # Should return HTML string
        assert isinstance(html, str)
        assert len(html) > 0

        # Should contain template content
        assert "<!DOCTYPE html>" in html
        assert "Test summary" in html
        assert "Bullet 1" in html
        assert "Bullet 2" in html

    def test_preview_update_with_empty_inputs(self):
        """Test that handle_preview_update handles empty inputs."""
        html = handle_preview_update("", [])

        # Should still return valid HTML
        assert isinstance(html, str)
        assert "<!DOCTYPE html>" in html

    def test_pdf_generation_handler(self):
        """Test that handle_pdf_generation creates PDF file."""
        # Create simple HTML
        html = "<html><body><h1>Test Resume</h1></body></html>"

        pdf_path, status, pdf_state = handle_pdf_generation(html)

        # Should return path, success message, and path state
        assert pdf_path is not None
        assert isinstance(pdf_path, str)
        assert "PDF generated successfully" in status
        assert pdf_state == pdf_path

        # File should exist
        path = Path(pdf_path)
        assert path.exists()
        assert path.suffix == ".pdf"

        # Clean up
        path.unlink()

    def test_pdf_generation_with_full_template(self):
        """Test PDF generation with complete resume template."""
        # Create canonical bullets structure
        canonical_bullets = [
            {"text": "Led development team", "bullet_id": "1", "section": "spins"},
            {"text": "Implemented new features", "bullet_id": "2", "section": "spins"},
            {"text": "Improved performance", "bullet_id": "3", "section": "spins"},
            {"text": "Developed Python applications", "bullet_id": "4", "section": "programmer"},
            {"text": "Created automated tests", "bullet_id": "5", "section": "programmer"},
            {"text": "Analyzed data trends", "bullet_id": "6", "section": "analyst"},
            {"text": "Created reports", "bullet_id": "7", "section": "analyst"}
        ]

        html = handle_preview_update(
            "Professional summary with experience in software development",
            canonical_bullets
        )

        pdf_path, status, pdf_state = handle_pdf_generation(html)

        # Should succeed
        assert pdf_path is not None
        assert "PDF generated successfully" in status

        # File should exist and have content
        path = Path(pdf_path)
        assert path.exists()
        assert path.stat().st_size > 0

        # Clean up
        path.unlink()

    def test_full_workflow(self, sample_inputs):
        """Test complete workflow from generation to PDF export."""
        # Skip if bullet file doesn't exist
        if not Path(sample_inputs["bullet_file"]).exists():
            pytest.skip("Bullet example file not found")

        # Step 1: Generate resume
        gen_result = handle_generate(
            sample_inputs["jd"],
            "Test Job Title",
            sample_inputs["company"],
            sample_inputs["info"],
            sample_inputs["bullet_file"],
            sample_inputs["job_change"]
        )

        json_output = gen_result[0]
        edit_summary = gen_result[1]
        edit_spins = gen_result[2]
        edit_programmer = gen_result[3]
        edit_analyst = gen_result[4]
        canonical_bullets = gen_result[15]  # New canonical bullets state

        # Verify generation succeeded
        assert "error" not in json_output
        assert edit_summary != ""

        # Step 2: Simulate editing (modify summary)
        edited_summary = edit_summary + " [EDITED]"

        # Step 3: Update preview with edited content (using canonical state)
        preview_html = handle_preview_update(
            edited_summary,
            canonical_bullets
        )

        # Verify edited content appears in preview
        assert "[EDITED]" in preview_html

        # Step 4: Generate PDF
        pdf_path, status, pdf_state = handle_pdf_generation(preview_html)

        # Verify PDF generation
        assert pdf_path is not None
        assert "PDF generated successfully" in status
        assert Path(pdf_path).exists()

        # Clean up
        Path(pdf_path).unlink()
