FROM pypy:3-7-buster AS build-image
RUN apt-get update
RUN apt-get install -y --no-install-recommends build-essential gcc python3-venv python3-pip

RUN python3 -m venv /opt/venv
# Make sure we use the virtualenv:
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip3 install -r requirements.txt


FROM pypy:3-7-buster AS run-image
COPY --from=build-image /opt/venv /opt/venv

WORKDIR /bot
COPY bot/ .
# Make sure we use the virtualenv:
ENV PATH="/opt/venv/bin:$PATH"
CMD [ "python3", "-u", "main.py" ]
