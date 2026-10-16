#!/bin/bash

format:
	uv run ruff format
	uv run ruff check --fix --show-fixes

lint:
	uv run ruff check
ifeq ('$(imports)', 'true')
	uv run pylint ./app
endif

tests:
	.venv/bin/alembic upgrade head
ifndef $(test_dir)
	$(eval test_dir=app/tests)
endif
	.venv/bin/pytest -v $(test_dir)

pre-push:
	make lint imports=true
ifndef $(test_dir)
	make tests
else
	make tests test_dir='./$(test_dir)'
endif


install:
	curl -LsSf https://astral.sh/uv/install.sh | sh
	sudo rm -f /usr/bin/uvx
	sudo ln -s ~/.local/bin/uvx /usr/bin/uvx # need for local precommit hooks
	sudo rm -f /usr/bin/uv # need for local precommit hooks
	sudo ln -s ~/.local/bin/uv /usr/bin/uv  # need for local precommit hooks
	uv sync
	sudo rm -f /usr/bin/pytest  # need for local precommit hooks
	sudo ln -s $(pwd)/.venv/bin/pytest /usr/bin/pytest  # need for local precommit hooks
	.venv/bin/pre-commit install && .venv/bin/pre-commit install -t pre-push # install pre-commit\pre-push hooks

run-tests:
	echo 'Test is running'

check-imports:
	uv run pylint ./app

init-database:
	set -a && . ./.env && set +a && \
	psql -v dbname="$$DATABASE__NAME" -v username="$$DATABASE__USER" -v password="$$DATABASE__PASSWORD" \
		-f system_sql/database_init.sql

reset-database:
	psql < system_sql/reset_database.sql

init-test-database:
	psql < system_sql/test_database_init.sql

reset-test-database:
	psql < system_sql/reset_test_database.sql

run-server:
	uv run python -m app.web_app

run-tasks:
	uv run faststream run app.consumer_app:app

migrate-docker:
	docker compose run --rm migrate

makemigrations-docker:
	docker compose run --rm -v $(CURDIR)/migrations:/app/migrations migrate \
		alembic revision --autogenerate -m "$(msg)"