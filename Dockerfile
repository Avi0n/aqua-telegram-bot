FROM python:3.7-stretch

COPY requirements.txt /tmp/

RUN pip install --no-cache-dir -r /tmp/requirements.txt

RUN adduser --uid 1000 --home /home/appuser appuser --disabled-password --quiet
WORKDIR /home/appuser
USER appuser

COPY . .

CMD [ "python3", "-u", "./main.py" ]
