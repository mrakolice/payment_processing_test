\c payment_processing;

DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;
ALTER DATABASE payment_processing OWNER TO payment_user;
GRANT ALL PRIVILEGES ON DATABASE payment_processing TO payment_user;
GRANT ALL ON SCHEMA public TO payment_user;