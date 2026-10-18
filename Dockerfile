FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    STREAMLIT_SERVER_HEADLESS=true DATA_DIR=/app/data PYTHONPATH=/app/src

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/ src/
RUN pip install . pytest

COPY app.py ./
COPY ui/ ui/
COPY tests/ tests/
COPY examples/ examples/

RUN useradd --create-home --uid 10001 researcher && mkdir -p /app/data && chown researcher /app/data
USER researcher

EXPOSE 8501
# Credentials only at run time: docker run --env-file .env ...
CMD ["streamlit", "run", "ui/streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
