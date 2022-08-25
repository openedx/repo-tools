.PHONY: help test dev-install install upgrade lint

help:				## display this help message
	@echo "Please use \`make <target>' where <target> is one of"
	@awk -F ':.*?## ' '/^[a-zA-Z]/ && NF==2 {printf "\033[36m  %-25s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST) | sort

test:				## run the tests
	pytest

dev-install:			## install everything to develop here
	pip install -r requirements/development.txt
	pip install -e .

install:			## install everything to run the tools
	pip install -r requirements/base.txt
	pip install -e .

COMMON_CONSTRAINTS_TXT=requirements/common_constraints.txt
.PHONY: $(COMMON_CONSTRAINTS_TXT)
$(COMMON_CONSTRAINTS_TXT):
	wget -O "$(@)" https://raw.githubusercontent.com/edx/edx-lint/master/edx_lint/files/common_constraints.txt || touch "$(@)"

upgrade: export CUSTOM_COMPILE_COMMAND=make upgrade
upgrade: $(COMMON_CONSTRAINTS_TXT)  ## update the requirements/*.txt files with the latest packages satisfying requirements/*.in
	pip install -qr requirements/pip-tools.txt
	pip-compile --allow-unsafe --rebuild -o requirements/pip.txt requirements/pip.in
	pip-compile --upgrade -o requirements/pip-tools.txt requirements/pip-tools.in
	pip install -qr requirements/pip.txt
	pip install -qr requirements/pip-tools.txt
	pip-compile --upgrade -o requirements/base.txt requirements/base.in
	pip-compile --upgrade -o requirements/development.txt requirements/development.in
	pip-compile --upgrade -o requirements/conventional_commits.txt edx_repo_tools/conventional_commits/extra.in
	pip-compile --upgrade -o requirements/repo_access_scraper.txt edx_repo_tools/repo_access_scraper/extra.in

lint:				## run pep8 and pylint
	pep8 || true
	pylint *.py edx_repo_tools tests || true
