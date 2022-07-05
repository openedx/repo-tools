.PHONY: test dev-install install upgrade lint

test:
	pytest

dev-install:
	pip install -r requirements/development.txt
	pip install -e .

install:
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
	bash post-pip-compile.sh \
		requirements/pip-tools.txt \
		requirements/base.txt \
		requirements/development.txt \
		requirements/conventional_commits.txt

lint:
	pep8 || true
	pylint *.py edx_repo_tools tests || true
