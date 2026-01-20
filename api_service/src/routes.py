from fastapi import APIRouter, HTTPException, Response, status
import uuid
import json
import pika
import psycopg2
from datetime import datetime
from pydantic import ValidationError

from shared.models import NotificationRequestBase, NotificationResponse, NotificationStatus
from shared.config import settings

router = APIRouter()

def get_db_connection():
    return psycopg2.connect(settings.DATABASE_URL)

def get_rabbitmq_channel():
    params = pika.URLParameters(settings.RABBITMQ_URL)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.queue_declare(queue='notifications', durable=True)
    return connection, channel

@router.post("/notifications", response_model=NotificationResponse, status_code=status.HTTP_202_ACCEPTED)
def create_notification(request: NotificationRequestBase):
    notification_id = str(uuid.uuid4())
    now = datetime.now()
    
    # 1. Store in Database
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO notification_requests (id, recipient, subject, message, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (notification_id, request.recipient, request.subject, request.message, NotificationStatus.ENQUEUED.value, now, now)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    # 2. Publish to RabbitMQ
    try:
        connection, channel = get_rabbitmq_channel()
        message_body = json.dumps({
            "id": notification_id,
            "recipient": request.recipient,
            "subject": request.subject,
            "message": request.message
        })
        channel.basic_publish(
            exchange='',
            routing_key='notifications',
            body=message_body,
            properties=pika.BasicProperties(
                delivery_mode=2,  # make message persistent
            ))
        connection.close()
    except Exception as e:
        # Rollback or log error - strictly speaking if queue fails we might want to fail the request or have a cleanup job. 
        # For this task, we will raise error but the DB record exists. 
        # A robust system typically does this in a transaction or uses the outbox pattern.
        # But per requirements "API service must store... before publishing".
        raise HTTPException(status_code=500, detail=f"Queue error: {str(e)}")

    return {
        "id": notification_id,
        "status": NotificationStatus.ENQUEUED,
        "message": "Notification request accepted and enqueued.",
        "recipient": request.recipient,
        "subject": request.subject
    }
