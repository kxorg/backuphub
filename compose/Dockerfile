FROM python:3.13-alpine AS builder

RUN apk add --no-cache gcc musl-dev python3-dev postgresql-dev

WORKDIR /build

COPY requirements.txt .

RUN python -m venv /opt/py

RUN /opt/py/bin/pip install --upgrade pip && \
    /opt/py/bin/pip install -r requirements.txt --no-cache-dir

FROM python:3.13-alpine AS final

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/py/bin:$PATH"

RUN apk add --no-cache bash

RUN addgroup -g 1000 bhgroup && \
    adduser -u 1000 -G bhgroup -s /bin/bash -D bhuser

WORKDIR /opt/bh

COPY --from=builder /opt/py /opt/py

COPY ./app .

COPY ./compose/entrypoint /entrypoint
COPY ./compose/start /start
COPY ./compose/celery/worker/start /start-celeryworker
COPY ./compose/celery/beat/start /start-celerybeat
COPY ./compose/celery/flower/start /start-flower

RUN sed -i 's/\r$//g' /entrypoint /start /start-celeryworker /start-celerybeat /start-flower && \
    chmod +x /entrypoint /start /start-celeryworker /start-celerybeat /start-flower

RUN mkdir -p /opt/bh/logs/app && \
    chown -R bhuser:bhgroup /opt/bh /opt/py

USER bhuser

EXPOSE 8000

ENTRYPOINT ["/entrypoint"]