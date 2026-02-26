.PHONY: help clean test dev-install install upgrade lint sync sync-constraints

help:				## display this help message
	@echo "Please use \`make <target>' where <target> is one of"
	@awk -F ':.*?## ' '/^[a-zA-Z]/ && NF==2 {printf "\033[36m  %-25s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST) | sort

clean:				## remove transient artifacts
	rm -rf .*cache *.egg-info .coverage build/ htmlcov/
	find . -name '__pycache__' -exec rm -rf {} +
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +

test:				## run the tests
	uv run pytest

dev-install:			## install everything to develop here (legacy command, use 'sync' instead)
	uv sync --all-extras --dev

install:			## install everything to run the tools
	uv sync

sync:				## sync dependencies from uv.lock file
	uv sync --all-extras --dev

sync-constraints:		## download and sync common_constraints.txt to pyproject.toml
	uv run python sync_constraints.py

upgrade: export CUSTOM_COMPILE_COMMAND=make upgrade
upgrade: sync-constraints	## update the uv.lock file with the latest packages (syncs constraints first)
	uv lock --upgrade

lint:				## run pylint
	uv run pylint *.py edx_repo_tools tests
