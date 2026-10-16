CREATE DATABASE test_payment_processing;
CREATE USER test_payment_user WITH PASSWORD 'password';
ALTER DATABASE test_payment_processing OWNER TO test_payment_user;
GRANT ALL PRIVILEGES ON DATABASE test_payment_processing TO test_payment_user;
