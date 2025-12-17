"""
Notification schema definitions.

Push notifications and web push subscriptions.
"""

from pydantic import BaseModel
from typing import Optional

class PushSubscriptionBase(BaseModel):
    endpoint: str
    p256dh: str
    auth: str

class PushSubscriptionCreate(PushSubscriptionBase):
    pass

class PushSubscriptionResponse(PushSubscriptionBase):
    id: int
    user_id: Optional[int] = None

    class Config:
        from_attributes = True
