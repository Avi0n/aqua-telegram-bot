FROM python:3.7

COPY . /app

WORKDIR /app

RUN pip install pip --upgrade && \
pip install mysqlclient python-telegram-bot emoji python-dotenv

CMD python ./main.py
