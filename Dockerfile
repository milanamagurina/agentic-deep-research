FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app.py .
COPY deep_research/ deep_research/
COPY tests/ tests/

# Run as an unprivileged user; run artifacts go to /app/runs (mount it to keep them).
RUN useradd --create-home --uid 10001 researcher && mkdir -p /app/runs && chown researcher /app/runs
USER researcher

# Credentials come from the environment at run time (docker run --env-file .env), never from the image.
ENTRYPOINT []
CMD ["python", "app.py"]
