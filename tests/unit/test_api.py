import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import sys
import os

# Put shared in path
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from api_service.src.main import app
from shared.models import NotificationStatus

client = TestClient(app)

@patch('api_service.src.routes.get_db_connection')
@patch('api_service.src.routes.get_rabbitmq_channel')
def test_create_notification_success(mock_rabbit, mock_db):
    # Mock DB
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_db.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    
    # Mock Rabbit
    mock_rabbit_conn = MagicMock()
    mock_rabbit_channel = MagicMock()
    mock_rabbit.return_value = (mock_rabbit_conn, mock_rabbit_channel)
    
    payload = {
        "recipient": "test@example.com",
        "subject": "Hello",
        "message": "World"
    }
    
    response = client.post("/api/notifications", json=payload)
    
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "ENQUEUED"
    assert data["recipient"] == "test@example.com"
    
    # Verify DB Insert
    mock_cursor.execute.assert_called_once()
    insert_sql = mock_cursor.execute.call_args[0][0]
    assert "INSERT INTO notification_requests" in insert_sql
    
    # Verify Queue Publish
    mock_rabbit_channel.basic_publish.assert_called_once()
    
@patch('api_service.src.routes.get_db_connection')
def test_create_notification_db_error(mock_db):
    mock_db.side_effect = Exception("DB Connection Failed")
    
    payload = {
        "recipient": "test@example.com",
        "subject": "Hello",
        "message": "World"
    }
    
    response = client.post("/api/notifications", json=payload)
    assert response.status_code == 500
    assert "Database error" in response.json()['detail']

def test_create_notification_invalid_input():
    payload = {
        "recipient": "invalid-email",
        "subject": "Hello",
        "message": "World"
    }
    response = client.post("/api/notifications", json=payload)
    assert response.status_code == 422 # FastAPI default validation error
