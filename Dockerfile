#FROM jfloff/alpine-python:3.7
FROM python:3.7-alpine

MAINTAINER Avi0n

WORKDIR /app

COPY ./requirements.txt /app

RUN apk --no-cache add libressl-dev musl-dev libffi-dev mariadb-dev build-base libjpeg-turbo-dev ffmpeg \
&& pip install --no-cache-dir -r requirements.txt

COPY . /app

CMD python main.py
