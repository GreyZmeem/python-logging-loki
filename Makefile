printMsg=printf "\033[36m\033[1m%-15s\033[0m\033[36m %-30s\033[0m\n"

.PHONY: test help run lint build dist

## use triple hashes ### to indicate main build targets
help:
	@awk 'BEGIN {FS = ":[^#]*? ### "} /^[a-zA-Z_-]+:[^#]* ### / {printf "\033[1m\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@awk 'BEGIN {FS = ":[^#]*? ## "} /^[a-zA-Z_-]+:[^#]* ## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
.DEFAULT_GOAL := help

install-tox: ### Install tox
	pip install tox

test: ### Run linting and tests
	tox run

upgrade-buildtools:
	pip install --upgrade pip
	pip install --upgrade setuptools
	pip install --upgrade wheel

ci-install: ### CI install
	make upgrade-buildtools
	make install-tox
