CREATE TABLE IF NOT EXISTS notification_requests (
    id VARCHAR(36) PRIMARY KEY, /* UUID */
    recipient VARCHAR(255) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    status VARCHAR(50) NOT NULL, /* ENQUEUED, PROCESSING, DELIVERED, FAILED */
    retries_attempted INTEGER DEFAULT 0,
    last_error_message TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_notification_recipient ON notification_requests (recipient);
CREATE INDEX IF NOT EXISTS idx_notification_status ON notification_requests (status);
