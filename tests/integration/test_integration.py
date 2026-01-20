import requests
import time
import psycopg2
import pytest
import os

# Configuration assuming default local ports
API_URL = "http://localhost:8000/api/notifications"
DB_DSN = "postgres://user:password@localhost:5432/notification_db"

def get_db_connection():
    return psycopg2.connect(DB_DSN)

def test_end_to_end_flow():
    # Only run if services are up (This is a manual integration test helper)
    try:
        requests.get("http://localhost:8000/health")
    except requests.exceptions.ConnectionError:
        pytest.skip("API not running. Start docker-compose to run integration tests.")

    # 1. Send Request
    payload = {
        "recipient": "integration@test.com",
        "subject": "Integration Test",
        "message": "Testing flow"
    }
    response = requests.post(API_URL, json=payload)
    assert response.status_code == 202
    data = response.json()
    notification_id = data['id']
    assert data['status'] == 'ENQUEUED'
    
    # 2. Poll Database for status change
    # Worker should pick it up and set to PROCESSING -> DELIVERED
    
    max_retries = 10
    success = False
    
    for _ in range(max_retries):
        time.sleep(1) # Wait for worker
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT status FROM notification_requests WHERE id = %s", (notification_id,))
            row = cur.fetchone()
            cur.close()
            conn.close()
            
            if row:
                status = row[0]
                print(f"Current status: {status}")
                if status == 'DELIVERED':
                    success = True
                    break
        except Exception as e:
            print(f"DB Error: {e}")
            
    assert success, f"Notification {notification_id} was not DELIVERED in time."

if __name__ == "__main__":
    test_end_to_end_flow()
    print("Integration test passed!")
