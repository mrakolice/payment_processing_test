-- Параметры передаются через psql -v: dbname, username, password.
-- Это нужно, чтобы не хардкодить значения из app/.env (локально — через make
-- init-database, в docker — через system_sql/init-db.sh при первом старте контейнера).
CREATE DATABASE :"dbname";
CREATE USER :"username" WITH PASSWORD :'password';
ALTER DATABASE :"dbname" OWNER TO :"username";
GRANT ALL PRIVILEGES ON DATABASE :"dbname" TO :"username";
