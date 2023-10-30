FROM python:latest

ENV PYTHONUNBUFFERED 1

RUN mkdir /django_app
WORKDIR /django_app

ADD requirements.txt requirements.txt
RUN pip install -r requirements.txt

ADD . /django_app/
