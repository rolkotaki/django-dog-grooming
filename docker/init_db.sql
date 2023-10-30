
-- these will be created automatically because of the environment variables that we provide in the docker-compose file
--CREATE DATABASE dog_grooming_website;
--CREATE USER dog_grooming_user WITH password 'yoursecretpassword';

ALTER ROLE dog_grooming_user SET client_encoding TO 'utf8';
ALTER ROLE dog_grooming_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE dog_grooming_user SET timezone TO 'UTC';
ALTER ROLE dog_grooming_user createdb;

GRANT ALL PRIVILEGES ON DATABASE dog_grooming_website TO dog_grooming_user;

GRANT ALL ON SCHEMA public TO dog_grooming_user;
GRANT ALL ON SCHEMA public TO public;

ALTER DATABASE dog_grooming_website OWNER TO dog_grooming_user;
