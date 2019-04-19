FROM jfloff/alpine-python:3.7

MAINTAINER Avi0n

COPY . /app

WORKDIR /app

RUN apk add --no-cache mariadb-dev build-base

RUN pip install pip --upgrade && \
pip install -r requirements.txt

CMD python ./main.py
