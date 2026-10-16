CREATE DATABASE payment_processing;
CREATE USER payment_user WITH PASSWORD 'password';
ALTER DATABASE payment_processing OWNER TO payment_user;
GRANT ALL PRIVILEGES ON DATABASE payment_processing TO payment_user;
