FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for psycopg2 and curl for healthcheck
RUN apt-get update && apt-get install -y libpq-dev gcc curl && rm -rf /var/lib/apt/lists/*

COPY worker_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared module
COPY shared /app/shared

# Copy service code
COPY worker_service /app/worker_service

# Set python path
ENV PYTHONPATH=/app

CMD ["python", "worker_service/src/worker.py"]
