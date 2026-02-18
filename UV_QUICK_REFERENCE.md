# uv Quick Reference Guide

## Essential Commands

### Installation & Setup

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all dependencies (first time setup)
uv sync --all-extras --dev

# Install only production dependencies
uv sync

# Install with specific extras
uv sync --extra repo_checks --extra audit_gh_users
```

### Running Commands

```bash
# Run tests
uv run pytest

# Run specific test file
uv run pytest tests/test_repo_checks.py

# Run linting
uv run pylint *.py edx_repo_tools tests

# Run any installed tool
uv run repo_checks --help
uv run audit_users --help
```

### Using Make Targets

```bash
# Install everything (recommended for development)
make sync

# Run tests
make test

# Run linting
make lint

# Update all dependencies
make upgrade
```

### Dependency Management

```bash
# Update all dependencies to latest compatible versions
uv lock --upgrade

# Update a specific package
uv lock --upgrade-package requests

# Regenerate lock file without upgrading
uv lock

# Sync after pulling changes (install/update dependencies)
uv sync --all-extras --dev
```

### Constraint Management

```bash
# Sync common constraints from edx-lint (recommended before upgrading)
make sync-constraints

# Or run the script directly
uv run python sync_constraints.py

# Full upgrade workflow (syncs constraints then updates lock file)
make upgrade
```

### Adding Dependencies

#### 1. Core Dependencies (needed by most tools)
Edit `pyproject.toml`:
```toml
[project]
dependencies = [
    "existing-package",
    "new-package>=1.0.0",  # Add here
]
```

#### 2. Development Dependencies (testing, linting)
Edit `pyproject.toml`:
```toml
[dependency-groups]
dev = [
    "pytest",
    "new-dev-tool",  # Add here
]
```

#### 3. Optional Dependencies (tool-specific)
Edit `pyproject.toml`:
```toml
[project.optional-dependencies]
my_tool = [
    "special-package",  # Add here
]
```

After editing, run:
```bash
uv lock         # Update lock file
uv sync --dev   # Install new dependencies
```

## Troubleshooting

### "Module not found" error
```bash
# Make sure dependencies are installed
uv sync --all-extras --dev
```

### "uv: command not found"
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Restart shell or source profile
source ~/.bashrc  # or ~/.zshrc
```

### Want to use traditional virtualenv
```bash
# uv creates .venv automatically
source .venv/bin/activate

# Now you can use commands directly without 'uv run'
pytest
pylint --help
```

### Clear cache and reinstall
```bash
# Remove virtual environment
rm -rf .venv

# Reinstall everything
uv sync --all-extras --dev
```

### Lock file conflicts after git merge
```bash
# Accept incoming lock file and regenerate
git checkout --theirs uv.lock
uv sync --all-extras --dev
```

## Environment Information

```bash
# Show Python version
uv run python --version

# Show installed packages
uv pip list

# Show dependency tree
uv tree

# Show package information
uv pip show package-name
```

## Common Workflows

### Daily Development
```bash
# 1. Pull latest changes
git pull

# 2. Update dependencies
uv sync --all-extras --dev

# 3. Make changes to code

# 4. Run tests
uv run pytest

# 5. Run linting
uv run pylint edx_repo_tools
```

### Syncing Constraints (Weekly/As Needed)
```bash
# 1. Sync constraints from edx-lint
make sync-constraints

# 2. Update lock file with new constraints
uv lock --upgrade

# 3. Install updated dependencies
uv sync --all-extras --dev

# 4. Test
uv run pytest

# 5. Commit changes
git add pyproject.toml uv.lock requirements/common_constraints.txt
git commit -m "Update constraints and dependencies"
```
