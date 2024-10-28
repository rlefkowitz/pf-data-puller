.PHONY=regen-requirements setup-environment run
SHELL=/bin/bash

regen-requirements: # regenerate requirements.txt package versions
	pip install pip-tools && cp requirements.txt requirements.in && sed -i '' 's/[><=].*//' requirements.txt && pip-compile --upgrade --no-annotate --no-header && rm requirements.in && pip install -r requirements.txt

setup-environment: # setup the environment for the first time
	./scripts/setup_environment.sh

run: # run the script
	@if [ ! -d "venv" ]; then make setup-environment; fi
	. venv/bin/activate && python scraper.py
