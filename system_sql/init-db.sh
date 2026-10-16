#!/bin/sh
# Запускается Postgres-образом из /docker-entrypoint-initdb.d только при первой
# инициализации пустого volume — то есть ровно тогда, когда БД ещё не создана.
# Значения берёт из переменных окружения контейнера (DATABASE__* из app/.env).
set -eu

psql -v ON_ERROR_STOP=1 \
    --username "$POSTGRES_USER" \
    --dbname postgres \
    -v dbname="$DATABASE__NAME" \
    -v username="$DATABASE__USER" \
    -v password="$DATABASE__PASSWORD" \
    -f /system_sql/database_init.sql
