from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from enum import Enum

class NotificationStatus(str, Enum):
    ENQUEUED = "ENQUEUED"
    PROCESSING = "PROCESSING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"

class NotificationRequestBase(BaseModel):
    recipient: EmailStr
    subject: str
    message: str

class NotificationResponse(BaseModel):
    id: str
    status: NotificationStatus
    message: str
    recipient: str
    subject: str
    
class NotificationDBModel(NotificationRequestBase):
    id: str
    status: NotificationStatus
    retries_attempted: int
    last_error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
