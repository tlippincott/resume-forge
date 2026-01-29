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
            "bullet_file": str(Path(__file__).parent.parent.parent / "bullet_libs" / "bullet_example.json"),
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

        # Should return 11 outputs (added job_title param and state_selected_bullet_file output)
        assert len(result) == 11

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

        # State outputs (5-9) - summary is string, others are lists
        assert isinstance(result[5], str)  # state_summary
        assert isinstance(result[6], list)  # state_spins
        assert isinstance(result[7], list)  # state_programmer
        assert isinstance(result[8], list)  # state_analyst
        assert isinstance(result[9], str)  # state_job_title
        assert isinstance(result[10], str)  # state_selected_bullet_file

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

        # Should return 11 outputs with error
        assert len(result) == 11
        assert "error" in result[0]

    def test_preview_update_handler(self):
        """Test that handle_preview_update generates HTML."""
        html = handle_preview_update(
            "Test summary",
            "Bullet 1\nBullet 2",
            "Prog bullet 1\nProg bullet 2",
            "Analyst bullet 1"
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
        html = handle_preview_update("", "", "", "")

        # Should still return valid HTML
        assert isinstance(html, str)
        assert "<!DOCTYPE html>" in html

    def test_pdf_generation_handler(self):
        """Test that handle_pdf_generation creates PDF file."""
        # Create simple HTML
        html = "<html><body><h1>Test Resume</h1></body></html>"

        pdf_path, status = handle_pdf_generation(html)

        # Should return path and success message
        assert pdf_path is not None
        assert isinstance(pdf_path, str)
        assert "PDF generated successfully" in status

        # File should exist
        path = Path(pdf_path)
        assert path.exists()
        assert path.suffix == ".pdf"

        # Clean up
        path.unlink()

    def test_pdf_generation_with_full_template(self):
        """Test PDF generation with complete resume template."""
        html = handle_preview_update(
            "Professional summary with experience in software development",
            "Led development team\nImplemented new features\nImproved performance",
            "Developed Python applications\nCreated automated tests",
            "Analyzed data trends\nCreated reports"
        )

        pdf_path, status = handle_pdf_generation(html)

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

        # Verify generation succeeded
        assert "error" not in json_output
        assert edit_summary != ""

        # Step 2: Simulate editing (modify summary)
        edited_summary = edit_summary + " [EDITED]"

        # Step 3: Update preview with edited content
        preview_html = handle_preview_update(
            edited_summary,
            edit_spins,
            edit_programmer,
            edit_analyst
        )

        # Verify edited content appears in preview
        assert "[EDITED]" in preview_html

        # Step 4: Generate PDF
        pdf_path, status = handle_pdf_generation(preview_html)

        # Verify PDF generation
        assert pdf_path is not None
        assert "PDF generated successfully" in status
        assert Path(pdf_path).exists()

        # Clean up
        Path(pdf_path).unlink()
