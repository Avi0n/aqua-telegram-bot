FROM jfloff/alpine-python:3.7

MAINTAINER Avi0n

WORKDIR /app

COPY ./requirements.txt /app

RUN apk add mariadb-dev build-base

RUN pip install -r requirements.txt

COPY . /app

CMD [ "python", "./main.py" ]
