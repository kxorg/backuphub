# FROM python:3.10-slim

# ENV PYTHONUNBUFFERED=1
# ENV PYTHONDONTWRITEBYTECODE=1

# EXPOSE 8000

# RUN apt-get update && apt-get install -y --no-install-recommends \
#     bash \
#     libpq5 \
#     && rm -rf /var/lib/apt/lists/*

# COPY local.requirements.txt /opt/local.requirements.txt

# RUN mkdir -p /opt/bh/logs/app && \
#     python3 -m venv /opt/py && \
#     /opt/py/bin/python3 -m pip install --upgrade pip && \
#     /opt/py/bin/python3 -m pip install -r /opt/local.requirements.txt --disable-pip-version-check && \
#     chmod -R 777 /opt

# ENV PATH="/opt/py/bin:$PATH"

# COPY ./app /opt/bh/
# WORKDIR /opt/bh/

# CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]



FROM python:3.10-alpine

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

EXPOSE 8000

COPY local.requirements.txt /opt/requirements.txt

RUN apk update && \
    apk add --no-cache \
        bash

RUN cd /opt/ && mkdir -p /opt/bh && python3 -m venv py && \
    /opt/py/bin/python3 -m pip install --upgrade pip && \
    /opt/py/bin/python3 -m pip install -r /opt/requirements.txt --no-build-isolation --disable-pip-version-check && \
    chmod -R 777 /opt && \
    mkdir -p /opt/bh/logs/app && \
    chmod 755 /opt/bh/logs

COPY ./compose/entrypoint /entrypoint
COPY ./compose/start /start
COPY ./compose/celery/worker/start /start-celeryworker
COPY ./compose/celery/beat/start /start-celerybeat
COPY ./compose/celery/flower/start /start-flower

RUN sed -i 's/\r$//g' /entrypoint && \
    sed -i 's/\r$//g' /start && \
    sed -i 's/\r$//g' /start-celeryworker && \
    sed -i 's/\r$//g' /start-celerybeat && \
    sed -i 's/\r$//g' /start-flower && \
    chmod +x /entrypoint && \
    chmod +x /start && \
    chmod +x /start-celeryworker && \
    chmod +x /start-celerybeat && \
    chmod +x /start-flower

ENV PATH="/opt/py/bin:$PATH"

COPY ./app /opt/bh/
WORKDIR /opt/bh/

ENTRYPOINT ["/entrypoint"]