.PHONY: test dev-install install upgrade install-pip-tools

test:
	py.test

install-pip-tools:
	pip install pip-tools

dev-install: install-pip-tools
	pip-sync dev-requirements.txt requirements.txt
	pip install -e .

install: install-pip-tools
	pip-sync requirements.txt
	pip install -e .

upgrade:
	pip-compile --upgrade dev-requirements.in
	pip-compile --upgrade requirements.in
