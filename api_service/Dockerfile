FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for psycopg2 and curl for healthcheck
RUN apt-get update && apt-get install -y libpq-dev gcc curl && rm -rf /var/lib/apt/lists/*

COPY api_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared module
COPY shared /app/shared

# Copy service code
COPY api_service /app/api_service

# Set python path so imports work
ENV PYTHONPATH=/app

CMD ["uvicorn", "api_service.src.main:app", "--host", "0.0.0.0", "--port", "8000"]
