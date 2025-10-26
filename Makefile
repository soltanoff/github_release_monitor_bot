.PHONY: static

docker_compose_path = "docker-compose.yml"

DC = docker-compose -f $(docker_compose_path)


format: # format your code according to project linter tools
	poetry run black app
	poetry run isort app

lint:
	poetry run black --check app
	poetry run isort --check app
	poetry run flake8 --inline-quotes '"'
	@# For some reason, mypy and pylint fails to resolve PYTHONPATH, set manually.
	PYTHONPATH=./app poetry run pylint app
	#PYTHONPATH=./app poetry run mypy --namespace-packages --show-error-codes app --check-untyped-defs --ignore-missing-imports --show-traceback

deps-audit:
	@# Ignore GHSA-vqfr-h8mv-ghfj, we're not using h11
	poetry run pip-audit --ignore-vuln GHSA-vqfr-h8mv-ghfj

app-up: # Up the project using docker-compose
	$(DC) up -d --build

down: # Down the project using docker-compose
	$(DC) down
