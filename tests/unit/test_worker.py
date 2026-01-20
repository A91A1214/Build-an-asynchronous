import pytest
from unittest.mock import MagicMock, patch
import json
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from worker_service.src.worker import process_message
from shared.models import NotificationStatus

@patch('worker_service.src.worker.get_db_connection')
@patch('worker_service.src.worker.update_status')
@patch('worker_service.src.worker.time.sleep') # Don't actually sleep
def test_process_message_success(mock_sleep, mock_update, mock_db):
    # Mock DB fetch
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_db.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    
    # Return a generic row: status, retries, recipient, subject, message
    mock_cursor.fetchone.return_value = (
        'ENQUEUED', 0, 'test@example.com', 'Sub', 'Msg'
    )
    
    # Mock RabbitMQ channel
    mock_ch = MagicMock()
    mock_method = MagicMock()
    mock_properties = MagicMock()
    
    body = json.dumps({
        "id": "123",
        "recipient": "test@example.com",
        "subject": "Sub",
        "message": "Msg"
    })
    
    process_message(mock_ch, mock_method, mock_properties, body)
    
    # Check status updates: First PROCESSING, then DELIVERED
    assert mock_update.call_count == 2
    mock_update.assert_any_call("123", NotificationStatus.PROCESSING.value)
    mock_update.assert_any_call("123", NotificationStatus.DELIVERED.value)
    
    # Check Ack
    mock_ch.basic_ack.assert_called_once()

@patch('worker_service.src.worker.get_db_connection')
@patch('worker_service.src.worker.update_status')
@patch('worker_service.src.worker.time.sleep')
def test_process_message_idempotency_delivered(mock_sleep, mock_update, mock_db):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_db.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    
    # Already DELIVERED
    mock_cursor.fetchone.return_value = (
        'DELIVERED', 0, 'test@example.com', 'Sub', 'Msg'
    )
    
    mock_ch = MagicMock()
    mock_method = MagicMock()
    mock_properties = MagicMock()
    
    body = json.dumps({"id": "123", "recipient": "t", "subject": "s", "message": "m"})
    
    process_message(mock_ch, mock_method, mock_properties, body)
    
    # Should NOT update status again
    mock_update.assert_not_called()
    
    # Should Ack
    mock_ch.basic_ack.assert_called_once()
