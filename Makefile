.PHONY: test dev-install install upgrade lint

test:
	pytest

dev-install:
	pip install -r requirements/development.txt
	pip install -e .

install:
	pip install -r requirements/base.txt
	pip install -e .

upgrade: ## Upgrade requirements with pip-tools
	pip install -qr requirements/pip-tools.txt
	pip-compile --allow-unsafe --rebuild -o requirements/pip.txt requirements/pip.in
	pip-compile --upgrade -o requirements/pip-tools.txt requirements/pip-tools.in
	pip-compile --upgrade -o requirements/base.txt requirements/base.in
	pip-compile --upgrade -o requirements/development.txt requirements/development.in
	pip-compile --upgrade -o requirements/conventional_commits.txt edx_repo_tools/conventional_commits/extra.in
	bash post-pip-compile.sh \
		requirements/pip-tools.txt \
		requirements/base.txt \
		requirements/development.txt \
		requirements/conventional_commits.txt

lint:
	pep8 || true
	pylint *.py edx_repo_tools tests || true
