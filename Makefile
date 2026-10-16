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
	psql < system_sql/database_init.sql

reset-database:
	psql < system_sql/reset_database.sql

init-test-database:
	psql < system_sql/test_database_init.sql

reset-test-database:
	psql < system_sql/reset_test_database.sql

create-router:
ifndef $(api_version)
	$(eval api_version=v1)
endif
#
	$(eval api_version_dir="app/api/$(api_version)")
	$(eval router_dir="app/api/$(api_version)/routes/$(router_name)")

# Создать каталог app/api/<api_version>, если его нет
# Если нет верхнеуровнего каталога <api_version>,
# создать app/api/<api_version>
# создать app/api/<api_version>/__init__.py, app/api/<api_version>/main.py
	mkdir -p "$(router_dir)"
	touch "$(api_version_dir)/__init__.py"
	touch "$(api_version_dir)/main.py"

# В app/api/<api_version>/main.py Написать
# from app.api.v1.routes.<router_name> import views as <router_name>
# router.include_router(<router_name>.router)
	printf "from app.api.v1.routes.$(router_name) import views as $(router_name)\nrouter.include_router($(router_name).router)" >> "$(api_version_dir)/main.py"

# В app/api/main.py Написать
# from app.api.<api_version> import main as <api_version>_api
# router.include_router(<api_version>_api.router, prefix='/<api_version>')
	printf "from app.api.$(api_version) import main as $(api_version)_api\nrouter.include_router($(api_version)_api.router, prefix='/$(api_version)')"

# Если нет app/api/<api_version>/routes, создать
# app/api/<api_version>/routes/__init__.py
	touch "$(api_version_dir)/routes/__init__.py"

# Если нет app/api/<api_version>/routes/<router_name> создать
# Создать app/api/<api_version>/routes/<router_name>/__init__.py
	touch "$(router_dir)/__init__.py"
# Создать app/api/<api_version>/routes/<router_name>/responses.py
	touch "$(router_dir)/responses.py"
# Создать app/api/<api_version>/routes/<router_name>/views.py
	touch "$(router_dir)/views.py"
# Создать app/api/<api_version>/routes/<router_name>/requests.py
	touch "$(router_dir)/requests.py"

# В app/api/<api_version>/routes/<router_name>/views.py написать
# import fastapi
#
# from app import dependencies as dep
# from app.api.<api_version>.routes.<router_name> import requests
# from app.api.<api_version>.routes.<router_name> import responses
#
# router = fastapi.APIRouter(prefix='/{router_name}', tags=['router_name'])
#
	printf "import fastapi\nfrom app import dependencies as dep\nfrom app.api.$(api_version).routes.$(router_name) import requests\nfrom app.api.$(api_version).routes.$(router_name) import responses\n\nrouter = fastapi.APIRouter(prefix='/$(router_name)', tags=['$(router_name)'])" >> "$(router_dir)/views.py"
# После всего сделать make format
	make format


run-server:
	uv run python -m app.web_app

run-tasks:
	uv run faststream run app.fast_stream_app:app