#!/usr/bin/env python
"""Test runner script for repo-search project."""

import os
import sys
import pytest
import subprocess
from pathlib import Path

def main():
    """Run tests for the repo-search project."""
    # Ensure we're running from the project root
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Set PYTHONPATH to include the src directory
    src_path = str(project_root / 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    
    # Handle any command line arguments
    args = sys.argv[1:]
    
    # Default arguments if none provided
    if not args:
        args = ["-v", "tests"]
    
    # Add pytest-specific arguments like -xvs for more verbose output
    if all(arg.startswith('-') or os.path.exists(arg) for arg in args):
        # If only options and paths are provided, add default behavior
        pass
    
    print(f"Running tests with arguments: {' '.join(args)}")
    print("=" * 80)
    
    # Run the tests
    result = pytest.main(args)
    
    # Print summary based on result
    if result == 0:
        print("=" * 80)
        print("All tests passed successfully!")
    else:
        print("=" * 80)
        print(f"Tests failed with exit code: {result}")
    
    return result

if __name__ == "__main__":
    sys.exit(main())
