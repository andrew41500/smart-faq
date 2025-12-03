FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    CHROMA_DIR=/data/chroma_db \
    SAMPLE_DOCS_DIR=/app/sample_docs

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

RUN mkdir -p /data/chroma_db

EXPOSE 8000

CMD ["gunicorn", "-b", "0.0.0.0:8000", "backend.app:create_app()"]


