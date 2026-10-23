PYTHON ?= python
.PHONY: install compile test demo benchmark figures reproduce foundry-test
install:
	npm ci --ignore-scripts
	$(PYTHON) -m pip install -r requirements-lock.txt
compile:
	npm run compile
test: compile
	$(PYTHON) -m pytest tests -q
foundry-test:
	forge test -vv
demo: compile
	$(PYTHON) -m src.demo
benchmark: compile
	$(PYTHON) -m src.benchmark
figures:
	$(PYTHON) -m src.generate_figures
reproduce: test demo benchmark figures
