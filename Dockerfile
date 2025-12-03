FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PORT=8000 \
    CHROMA_DIR=/data/chroma_db \
    SAMPLE_DOCS_DIR=/app/sample_docs

WORKDIR /app

# Install system dependencies and clean up in one layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /data/chroma_db /app/sample_docs

EXPOSE 8000

CMD ["gunicorn", "-b", "0.0.0.0:8000", "backend.app:create_app()"]


