#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the utils package initialization.

This module contains tests for the __init__.py module of the utils package,
ensuring proper module initialization, import functionality, version tracking,
and API surface consistency.
"""

import importlib
import sys
import os
import pytest
from unittest.mock import patch
from pathlib import Path


# Helper function to get the path to the utils __init__.py file
def get_utils_init_path():
    """Get the path to the utils __init__.py file."""
    # Start with the current file's directory
    current_dir = Path(__file__).parent
    # Navigate to the utils directory
    utils_dir = current_dir.parent.parent / 'src' / 'utils'
    return utils_dir / '__init__.py'


class TestUtilsInit:
    """Test class for the utils package initialization."""

    def test_version_info_exists(self):
        """Test that version information exists and is properly formatted."""
        # Import directly from the utils package
        from src.utils import __version__, __author__, __email__, __status__
        
        # Check that version info exists
        assert __version__, "__version__ should be defined"
        assert __author__, "__author__ should be defined"
        assert __email__, "__email__ should be defined"
        assert __status__, "__status__ should be defined"
        
        # Check version format (should be in semver format: X.Y.Z)
        version_parts = __version__.split('.')
        assert len(version_parts) == 3, "Version should be in X.Y.Z format"
        assert all(part.isdigit() for part in version_parts), "Version parts should be numeric"
        
        # Check email format
        assert '@' in __email__, "Email should contain @ symbol"
        assert '.' in __email__.split('@')[1], "Email domain should contain a dot"
        
        # Check status is a valid value
        valid_statuses = ['Development', 'Alpha', 'Beta', 'Production']
        assert __status__ in valid_statuses, f"Status should be one of {valid_statuses}"

    def test_all_modules_importable(self):
        """Test that all utility modules can be imported without errors."""
        from src.utils import __all__
        
        for module_name in __all__:
            # Attempt to import each module
            module = importlib.import_module(f"src.utils.{module_name}")
            assert module is not None, f"Failed to import {module_name}"

    def test_all_variable_matches_imports(self):
        """Test that __all__ contains all the modules that are imported."""
        from src.utils import __all__
        
        # Get the list of modules that are imported in __init__.py
        init_path = get_utils_init_path()
        with open(init_path, "r") as f:
            init_content = f.read()
        
        # Extract import statements
        import_lines = [line.strip() for line in init_content.split('\n') 
                      if line.strip().startswith('from . import')]
        
        imported_modules = []
        for line in import_lines:
            # Extract module name from 'from . import module_name'
            module = line.replace('from . import', '').strip()
            imported_modules.append(module)
        
        # Check that all imported modules are in __all__
        for module in imported_modules:
            assert module in __all__, f"{module} is imported but not in __all__"
        
        # Check that all modules in __all__ are imported
        for module in __all__:
            assert module in imported_modules, f"{module} is in __all__ but not imported"

    def test_import_order_prevents_circular_dependencies(self):
        """Test that the import order in __init__.py prevents circular dependencies."""
        # This test verifies the import order by checking the module dependencies
        # against the actual import order in __init__.py
        
        init_path = get_utils_init_path()
        with open(init_path, "r") as f:
            init_content = f.read()
        
        # Extract import statements
        import_lines = [line.strip() for line in init_content.split('\n') 
                      if line.strip().startswith('from . import')]
        
        # Get the actual import order
        actual_import_order = []
        for line in import_lines:
            module = line.replace('from . import', '').strip()
            actual_import_order.append(module)
        
        # Define the expected dependency order based on the comments in __init__.py
        # Core utilities with no internal dependencies should come first
        core_utils = ['logging_utils', 'error_utils', 'time_utils', 'validation_utils']
        # File and security utilities come next
        file_security_utils = ['file_utils', 'security_utils']
        # External service integration utilities follow
        service_utils = ['retry_utils', 's3_utils', 'rabbitmq_utils']
        # OCR processing utilities come last
        ocr_utils = ['image_utils', 'text_utils', 'tensorflow_utils']
        
        expected_order_groups = [core_utils, file_security_utils, service_utils, ocr_utils]
        
        # Check that the actual import order follows the expected dependency groups
        current_group_index = 0
        for module in actual_import_order:
            # Find which group this module belongs to
            group_found = False
            for i, group in enumerate(expected_order_groups):
                if module in group:
                    group_found = True
                    # Ensure we're not going backwards in the group order
                    assert i >= current_group_index, \
                        f"Module {module} from group {i} imported after modules from group {current_group_index}"
                    current_group_index = i
                    break
            
            assert group_found, f"Module {module} not found in any expected dependency group"

    def test_api_surface_consistency(self):
        """Test that the API surface is consistent and well-defined."""
        from src.utils import __all__
        
        # Check that __all__ is a list or tuple
        assert isinstance(__all__, (list, tuple)), "__all__ should be a list or tuple"
        
        # Check that all entries in __all__ are strings
        assert all(isinstance(module, str) for module in __all__), "All entries in __all__ should be strings"
        
        # Check for duplicates in __all__
        assert len(__all__) == len(set(__all__)), "__all__ should not contain duplicates"
        
        # Check that all modules in __all__ end with _utils
        assert all(module.endswith('_utils') for module in __all__), \
            "All utility modules should follow the naming convention of ending with '_utils'"

    def test_import_order_matches_dependency_comments(self):
        """Test that the import order matches the dependency comments in the file."""
        init_path = get_utils_init_path()
        with open(init_path, "r") as f:
            init_content = f.read()
        
        # Extract the dependency comments and the actual imports
        lines = init_content.split('\n')
        comment_sections = []
        current_section = []
        in_comment_section = False
        
        for line in lines:
            line = line.strip()
            if line.startswith('# ') and not in_comment_section and 'utilities' in line.lower():
                in_comment_section = True
                current_section = [line]
            elif in_comment_section and line.startswith('# '):
                current_section.append(line)
            elif in_comment_section and line.startswith('from . import'):
                # End of comment section, add the import
                current_section.append(line)
                comment_sections.append(current_section)
                in_comment_section = False
            elif in_comment_section and not line:
                # Empty line, continue collecting comments
                continue
            elif in_comment_section:
                # Non-comment line, end the section
                comment_sections.append(current_section)
                in_comment_section = False
        
        # Check that each comment section is followed by appropriate imports
        for section in comment_sections:
            comments = [line for line in section if line.startswith('# ')]
            imports = [line for line in section if line.startswith('from . import')]
            
            if not imports:
                continue  # Skip sections without imports
            
            # Check that the comments describe the imports that follow
            for import_line in imports:
                module = import_line.replace('from . import', '').strip()
                # Check if any comment in this section mentions this module or its category
                module_mentioned = any(module in comment.lower() for comment in comments)
                category_mentioned = any(module.replace('_utils', '') in comment.lower() for comment in comments)
                
                assert module_mentioned or category_mentioned, \
                    f"Module {module} is not described in the preceding comments: {comments}"

    @patch('importlib.import_module')
    def test_module_import_resilience(self, mock_import_module):
        """Test that the package handles import errors gracefully."""
        # Configure the mock to raise ImportError for tensorflow_utils
        def side_effect(name, *args, **kwargs):
            if name == 'src.utils.tensorflow_utils' or name.endswith('.tensorflow_utils'):
                raise ImportError(f"Simulated import error for {name}")
            # For all other imports, call the real import_module
            return importlib.import_module(name, *args, **kwargs)
        
        mock_import_module.side_effect = side_effect
        
        # Attempt to import the utils package
        with pytest.raises(ImportError) as excinfo:
            # Force a reload to trigger the imports again
            if 'src.utils' in sys.modules:
                del sys.modules['src.utils']
            import src.utils
        
        # Verify the error message
        assert "tensorflow_utils" in str(excinfo.value), "Error should mention the problematic module"


if __name__ == "__main__":
    pytest.main(['-xvs', __file__])