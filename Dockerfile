#FROM jfloff/alpine-python:3.7
FROM python:3.7-alpine

MAINTAINER Avi0n

COPY requirements.txt /tmp/

RUN apk --no-cache add libressl-dev musl-dev libffi-dev mariadb-dev build-base libjpeg-turbo-dev ffmpeg \
&& pip install --no-cache-dir -r /tmp/requirements.txt

RUN adduser -u 1000 -S appuser -h /home/appuser
WORKDIR /home/appuser
USER appuser

COPY . .

CMD [ "python", "-u", "./main.py" ]
