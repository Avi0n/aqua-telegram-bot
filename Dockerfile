FROM pypy:3

COPY requirements.txt /tmp/

RUN pip install --no-cache-dir -r /tmp/requirements.txt

RUN adduser --uid 1000 --home /home/appuser appuser --disabled-password --quiet
WORKDIR /home/appuser
USER appuser

COPY . .

CMD [ "pypy3", "-u", "./main.py" ]
