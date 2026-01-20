import pika
import psycopg2
import json
import time
import os
import sys
import random

# Add parent directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from shared.models import NotificationStatus
from shared.config import settings

def get_db_connection():
    return psycopg2.connect(settings.DATABASE_URL)

def update_status(notification_id, status, error_message=None):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        if error_message:
            cur.execute(
                "UPDATE notification_requests SET status = %s, last_error_message = %s, updated_at = NOW() WHERE id = %s",
                (status, error_message, notification_id)
            )
        else:
            cur.execute(
                "UPDATE notification_requests SET status = %s, updated_at = NOW() WHERE id = %s",
                (status, notification_id)
            )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error updating status for {notification_id}: {e}")

def get_notification(notification_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT status, retries_attempted, recipient, subject, message FROM notification_requests WHERE id = %s", (notification_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row

def increment_retries(notification_id, error_message):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE notification_requests SET retries_attempted = retries_attempted + 1, last_error_message = %s, updated_at = NOW() WHERE id = %s",
        (error_message, notification_id)
    )
    conn.commit()
    cur.close()
    conn.close()

def process_message(ch, method, properties, body):
    data = json.loads(body)
    notification_id = data.get('id')
    recipient = data.get('recipient')
    
    print(f"Received message for notification: {notification_id}")

    # 1. Fetch from DB / Idempotency Check
    try:
        row = get_notification(notification_id)
        if not row:
            print(f"Notification {notification_id} not found in DB. Acking to discard.")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        current_status, retries, db_recipient, db_subject, db_message = row
        
        if current_status == NotificationStatus.DELIVERED.value:
            print(f"Notification {notification_id} already DELIVERED. Skipping.")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return
            
    except Exception as e:
        print(f"DB Error fetching {notification_id}: {e}")
        # Nack and requeue if transient DB issue? Or retry logic?
        # For simplicity, we might Nack.
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        return

    # 2. Update to PROCESSING
    update_status(notification_id, NotificationStatus.PROCESSING.value)

    # 3. Simulate Delivery
    try:
        print(f"Simulating delivery to {recipient}...")
        time.sleep(random.uniform(1, 3)) # Simulate work
        
        # Random failure for demonstration? (Optional, maybe not for main flow unless requested)
        # Assuming success for now.
        
        print(f"Successfully delivered notification {notification_id}")
        update_status(notification_id, NotificationStatus.DELIVERED.value)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print(f"Error delivering {notification_id}: {e}")
        
        if retries < settings.MAX_RETRIES:
            increment_retries(notification_id, str(e))
            print(f"Retrying logic... Attempt {retries + 1}/{settings.MAX_RETRIES}")
            # We can basically 'Nack' with requeue=True to put it back on queue
            # Or we can publish to a retry queue with delay.
            # RabbitMQ doesn't natively support delay without plugins.
            # For this 'robust' task, Nack with Requeue is simple but loops fast.
            # Ideally: Use Dead Letter Exchange with TTL for backoff.
            # For this scope: Simple Nack(requeue=True) is okay but let's sleep briefly to prevent tight loop if we can.
            
            # Actually, standard retry pattern in AMQP:
            # Requeue goes to back of queue. If queue empty, instant retry.
            # Let's simple ack and republish? Or basic nack.
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        else:
            print(f"Max retries reached for {notification_id}. Marking FAILED.")
            update_status(notification_id, NotificationStatus.FAILED.value, str(e))
            # Ack to remove from queue, maybe publish to DLQ (Conceptual)
            ch.basic_ack(delivery_tag=method.delivery_tag)

def start_worker():
    # Health check server (simple thread)
    from threading import Thread
    from http.server import HTTPServer, BaseHTTPRequestHandler

    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/health':
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"OK")
            else:
                self.send_response(404)
                self.end_headers()
    
    def run_health_server():
        server = HTTPServer(('0.0.0.0', 8001), HealthHandler)
        print("Health check server running on port 8001")
        server.serve_forever()

    t = Thread(target=run_health_server, daemon=True)
    t.start()

    # RabbitMQ Connection
    while True:
        try:
            params = pika.URLParameters(settings.RABBITMQ_URL)
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            channel.queue_declare(queue='notifications', durable=True)
            
            # Set prefetch count for fair dispatch
            channel.basic_qos(prefetch_count=1)
            
            channel.basic_consume(queue='notifications', on_message_callback=process_message)
            
            print("Worker started. Waiting for messages...")
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError:
            print("Connection to RabbitMQ failed. Retrying in 5s...")
            time.sleep(5)
        except Exception as e:
            print(f"Worker Exception: {e}")
            time.sleep(5)

if __name__ == "__main__":
    start_worker()
