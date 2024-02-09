# Django Dog Grooming Salon
[![Run Tests](https://github.com/rolkotaki/django-dog-grooming/actions/workflows/run_tests.yml/badge.svg)](https://github.com/rolkotaki/django-dog-grooming/actions/workflows/run_tests.yml)
[![codecov](https://codecov.io/gh/rolkotaki/django-dog-grooming/graph/badge.svg?token=P78JBHZNZY)](https://codecov.io/gh/rolkotaki/django-dog-grooming)
<br><br>Website for a dog grooming salon.

## Description

This website is intended to satisfy the needs of a Hungarian local dog grooming salon. The salon offers several services 
that logged-in users can book. Staff users can see and manage all bookings.<br>
The main feautres of the website are:
* Sign up and log in
* Personal data and password change
* Booking of services
* Booking management (different for users and staff)
* Gallery
* Admin APIs to:
  * Create/update/delete services and contact information
  * Manage bookings
  * Manage the gallery
  * Search or cancel users

## Run With Docker Compose

Download the source code and go to the root of the repository.<br>
Run docker compose to start a clean instance of the website. The database data is mapped into the `docker/postgres_data` folder, so changes will be kept if you 
run it again.
```
docker-compose up -d
```
Stop and remove all containers:
```
docker-compose down
```

## Run Locally

The settings expect you to have PostgreSQL, so make sure that you have it running either locally or in a Docker container 
for example. You can use the image from the docker compose file.<br>
Run the following init script to prepare the application database user and the database:
```
CREATE DATABASE dog_grooming_website;
CREATE USER dog_grooming_user WITH password 'yoursecretpassword';
ALTER ROLE dog_grooming_user SET client_encoding TO 'utf8';
ALTER ROLE dog_grooming_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE dog_grooming_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE dog_grooming_website TO dog_grooming_user;
ALTER DATABASE dog_grooming_website OWNER TO dog_grooming_user;
ALTER ROLE dog_grooming_user createdb;
```
*Feel free to use a different database and change the database settings in the `settings.py`.*<br>

For emails I use [SendGrid](https://sendgrid.com/), but feel free to use what you prefer and change the settings (and probably code) accordingly.

Download the source code and go to the root of the repository.<br>

Add a `config.yml` file to store your database and email config or use environment variables *(check the settings in the `settings.py`)*:
```
postgresql_dog_grooming:
  name: dog_grooming_website
  user: dog_grooming_user
  password: yoursecretpassword
  host: localhost
  port: 5432
  test_db_name: dog_grooming_website_test

dog_grooming_email:
  sendgrid_api_key: YOUR_API_KEY
  sender: sender@mail.com
  admins:
    first_admin_name: first_admin@mail.com
```

Create the virtual environment and install the requirements:
```
python3 -m venv env
source env/bin/activate
pip3 install -r requirements.txt
```
Apply the migrations:
```
python3 manage.py migrate
```
Create the superuser:
```
python3 manage.py createsuperuser
```
Run the server (by default it will run on port 8000):
```
python3 manage.py runserver
```
Open in the browser: [127.0.0.1:8000](http://127.0.0.1:8000/)

## Run Tests

Run all the tests from the repository root:
```
python3 manage.py test
```
Run tests with coverage:
```
coverage run manage.py test
coverage html
```

## Multilanguage Management

The translations are in the `locale` folder, inside you will have a subfolder for each language. In case of adding new or 
updating existing translations we can do the following steps.<br>
Create the translation files *(from the repository root)*:
```
django-admin makemessages -all --ignore=env --ignore=docker
```
Compile the translations after providing them:
```
django-admin compilemessages --ignore=env --ignore=docker
```
<br>
Python version used for the development: Python 3.9.6