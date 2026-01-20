# Asynchronous Notification Service

A robust backend service for handling asynchronous notification processing using FastAPI, RabbitMQ, PostgreSQL, and Docker.

## Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Setup Instructions](#setup-instructions)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Design Choices](#design-choices)

## Overview
This service decouples notification requests from delivery using a message queue. It consists of:
1.  **API Service**: Accepts notification requests, validates them, saves to DB, and enqueues them.
2.  **Worker Service**: Consumes messages, simulates delivery, and updates DB status.
3.  **RabbitMQ**: Message broker.
4.  **PostgreSQL**: Persistent storage for notification state.

## Architecture
- **API**: FastAPI (Python)
- **Worker**: Python script
- **Queue**: RabbitMQ
- **Database**: PostgreSQL
- **Orchestration**: Docker Compose

## Setup Instructions

### Prerequisites
- Docker and Docker Compose installed.

### Running the Application
1.  Clone the repository (if applicable).
2.  Navigate to the project root:
    ```bash
    cd my-notification-service
    ```
3.  Start the services:
    ```bash
    docker-compose up --build
    ```
4.  The API will be available at `http://localhost:8002`.
5.  Management UI for RabbitMQ at `http://localhost:15672` (User: guest, Pass: guest).

## API Documentation

### POST /api/notifications
Enqueues a new notification.

**Request Body**
```json
{
    "recipient": "user@example.com",
    "subject": "Hello",
    "message": "Welcome to our service!"
}
```

**Response (202 Accepted)**
```json
{
    "id": "uuid-string",
    "status": "ENQUEUED",
    "message": "Notification request accepted and enqueued.",
    "recipient": "user@example.com",
    "subject": "Hello"
}
```

**Response (422/400 Bad Request)**
Invalid input data.

### GET /health
Health check endpoint.
Returns `{"status": "ok"}`.

## Testing

### Unit Tests
Located in `tests/unit`.
To run locally (outside docker), install dependencies and run:
```bash
pip install -r api_service/requirements.txt
pip install -r worker_service/requirements.txt
pip install pytest httpx
pytest tests/unit
```

### Integration Tests
To manually verify integration:
1.  Start services with `docker-compose up`.
2.  Send a POST request to the API.
    ```bash
    curl -X POST http://localhost:8002/api/notifications \
    -H "Content-Type: application/json" \
    -d '{"recipient": "test@test.com", "subject": "Test", "message": "Body"}'
    ```
3.  Check API logs to see `Accepted`.
4.  Check Worker logs (`docker-compose logs -f worker`) to see:
    - Processing message...
    - Simulating delivery...
    - Successfully delivered...
5.  Connect to DB to verify status is `DELIVERED`:
    ```bash
    docker-compose exec db psql -U user -d notification_db -c "SELECT * FROM notification_requests;"
    ```

## Design Choices

### Message Queue (RabbitMQ)
Chosen for its reliability and support for acknowledgments. It allows decoupling the high-throughput API from the slower delivery process.

### Idempotency
The worker checks the database status before processing. if the status is already `DELIVERED` for a given ID, processing is skipped. This prevents duplicate deliveries if a message is redelivered (e.g., due to worker crash after delivery but before ack).

### Retry Mechanism
The worker implements a retry loop (up to `MAX_RETRIES`). If delivery fails, it increments the retry count in the database. In a real-world scenario, we would use Dead Letter Queues (DLQ) or exponential backoff with delayed queues (e.g., RabbitMQ `x-delayed-message` plugin) to avoid busy-waiting. For this implementation, we use basic Nack/Requeue logic or simple internal retries.

### Docker
All services are containerized to ensure consistent environments and easy deployment. Health checks ensure services start in the correct order (e.g., API waits for DB and RabbitMQ).
