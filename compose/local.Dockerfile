FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY local.requirements.txt /opt/local.requirements.txt

RUN mkdir -p /opt/bh/logs/app && \
    python3 -m venv /opt/py && \
    /opt/py/bin/python3 -m pip install --upgrade pip && \
    /opt/py/bin/python3 -m pip install -r /opt/local.requirements.txt --disable-pip-version-check && \
    chmod -R 777 /opt

ENV PATH="/opt/py/bin:$PATH"

COPY ./app /opt/bh/
WORKDIR /opt/bh/

CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
