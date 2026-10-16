\c test_payment_processing;

DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;
ALTER DATABASE test_payment_processing OWNER TO test_payment_user;
GRANT ALL PRIVILEGES ON DATABASE test_payment_processing TO test_payment_user;
GRANT ALL ON SCHEMA public TO test_connectors;