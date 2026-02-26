#!/usr/bin/env python3
"""
Script to sync common_constraints.txt into pyproject.toml.

This script downloads the common_constraints.txt file from edx-lint and
updates the [tool.uv.constraint-dependencies] section in pyproject.toml.
"""

import re
import sys
from pathlib import Path
from urllib.request import urlopen

COMMON_CONSTRAINTS_URL = "https://raw.githubusercontent.com/edx/edx-lint/master/edx_lint/files/common_constraints.txt"
PYPROJECT_PATH = Path(__file__).parent / "pyproject.toml"
CONSTRAINTS_FILE_PATH = (
    Path(__file__).parent / "requirements" / "common_constraints.txt"
)


def download_constraints():
    """Download the common_constraints.txt file."""
    print(f"Downloading constraints from {COMMON_CONSTRAINTS_URL}...")
    try:
        with urlopen(COMMON_CONSTRAINTS_URL) as response:
            content = response.read().decode("utf-8")

        # Save to requirements directory for reference
        CONSTRAINTS_FILE_PATH.parent.mkdir(exist_ok=True)
        CONSTRAINTS_FILE_PATH.write_text(content)
        print(f"Saved constraints to {CONSTRAINTS_FILE_PATH}")
        return content
    except Exception as e:
        print(f"Error downloading constraints: {e}", file=sys.stderr)
        # Try to read from local file if download fails
        if CONSTRAINTS_FILE_PATH.exists():
            print("Using existing local constraints file")
            return CONSTRAINTS_FILE_PATH.read_text()
        raise


def parse_constraints(content):
    """
    Parse constraints from common_constraints.txt.

    Returns a list of constraint strings suitable for pyproject.toml.
    """
    constraints = []

    for line in content.split("\n"):
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith("#"):
            continue

        # Parse constraint (e.g., "Django<6.0" or "pip<26.0")
        # Keep the constraint as-is
        constraints.append(line)

    return constraints


def update_pyproject_toml(constraints):
    """
    Update pyproject.toml with the new constraints.

    This function updates the [tool.uv.constraint-dependencies] section.
    """
    if not PYPROJECT_PATH.exists():
        print(f"Error: {PYPROJECT_PATH} not found", file=sys.stderr)
        sys.exit(1)

    content = PYPROJECT_PATH.read_text()

    # Build the new constraint-dependencies section
    constraints_section = "[tool.uv]\nconstraint-dependencies = [\n"
    constraints_section += "    # Downloaded from edx-lint common_constraints.txt\n"
    constraints_section += (
        "    # DO NOT EDIT - Use 'python sync_constraints.py' to update\n"
    )

    for constraint in constraints:
        # Escape quotes if needed
        constraint_str = constraint.replace('"', '\\"')
        constraints_section += f'    "{constraint_str}",\n'

    # Add local constraint (greenlet)
    constraints_section += "    # Local constraint\n"
    constraints_section += '    "greenlet>3.0.1",  # playwright and sqlalchemy requirements conflict for greenlet<=3.0.1\n'
    constraints_section += "]\n"

    # Find and replace the [tool.uv] section
    # Pattern to match [tool.uv] section with constraint-dependencies
    pattern = r"\[tool\.uv\]\s*\nconstraint-dependencies\s*=\s*\[.*?\]"

    if re.search(pattern, content, re.DOTALL):
        # Replace existing section
        new_content = re.sub(
            pattern, constraints_section.rstrip(), content, flags=re.DOTALL
        )
    else:
        # Check if [tool.uv] exists without constraint-dependencies
        if "[tool.uv]" in content:
            # Insert constraint-dependencies into existing [tool.uv]
            new_content = content.replace("[tool.uv]", constraints_section.rstrip())
        else:
            # Add new [tool.uv] section at the end
            new_content = content.rstrip() + "\n\n" + constraints_section

    PYPROJECT_PATH.write_text(new_content)
    print(f"Updated {PYPROJECT_PATH}")


def main():
    """Main function."""
    print("Syncing common_constraints.txt to pyproject.toml...")

    # Download constraints
    constraints_content = download_constraints()

    # Parse constraints
    constraints = parse_constraints(constraints_content)
    print(f"Found {len(constraints)} constraints")

    # Update pyproject.toml
    update_pyproject_toml(constraints)

    print(
        "\nDone! Run 'uv lock --upgrade' to update the lock file with the new constraints."
    )


if __name__ == "__main__":
    main()
