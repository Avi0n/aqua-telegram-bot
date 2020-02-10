FROM python:3.7-slim AS install-image
RUN apt-get update
RUN apt-get install -y --no-install-recommends build-essential gcc

RUN python -m venv /opt/venv
# Make sure we use the virtualenv:
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install -r requirements.txt


FROM python:3.7-slim AS build-image
COPY --from=install-image /opt/venv /opt/venv

COPY main.py .
COPY get_source.py .

# Make sure we use the virtualenv:
ENV PATH="/opt/venv/bin:$PATH"
CMD [ "python3", "-u", "main.py" ]
