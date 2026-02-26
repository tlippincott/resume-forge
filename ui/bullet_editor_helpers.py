"""Helper functions for bullet library editor.

DEPRECATED: Most business logic has been moved to app layer.
This file now re-exports functions for backward compatibility.
"""

from typing import Tuple, List
from app.text_processors import text_to_bullets, bullets_to_text
from app.validators import (
    validate_bullet,
    validate_bullets_text,
    validate_role_name,
    count_bullets,
    get_validation_summary
)
from app.bullet_library_manager import (
    load_bullet_library,
    save_bullet_library,
    create_new_bullet_library,
    rows_to_section_summary,   # NEW
)


# Backward compatibility - all functions are re-exported from app layer
# Original implementations have been removed

# All functions are now imported from app layer modules above
# This file serves as a re-export shim for backward compatibility
