.PHONY: test dev-install install upgrade lint

test:
	py.test

dev-install:
	pip install -r requirements/base.txt
	pip install -r requirements/development.txt
	pip install -e .

install:
	pip install -r requirements/base.txt
	pip install -e .

upgrade: ## Upgrade requirements with pip-tools
	pip install -qr requirements/pip-tools.txt
	pip-compile --upgrade -o requirements/pip-tools.txt requirements/pip-tools.in
	pip-compile --upgrade -o requirements/base.txt requirements/base.in
	pip-compile --upgrade -o requirements/development.txt requirements/development.in
	bash post-pip-compile.sh \
		requirements/pip-tools.txt \
		requirements/base.txt \
		requirements/development.txt

lint:
	pep8 || true
	pylint *.py edx_repo_tools age tests || true
