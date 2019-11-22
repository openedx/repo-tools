.PHONY: upgrade

help: ## display this help message
	@echo "Please use \`make <target>' where <target> is one of"
	@grep '^[a-zA-Z]' $(MAKEFILE_LIST) | sort | awk -F ':.*?## ' 'NF==2 {printf "\033[36m  %-25s\033[0m %s\n", $$1, $$2}'

upgrade: export CUSTOM_COMPILE_COMMAND=make upgrade
upgrade: ## update the pip requirements files to use the latest releases satisfying our constraints
	pip install -q --upgrade pip-tools
	pip-compile -v --no-emit-trusted-host --no-index --rebuild --upgrade -o requirements.txt requirements.in
