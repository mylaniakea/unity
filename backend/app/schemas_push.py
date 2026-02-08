"""
Pydantic schemas for web push subscriptions.
"""
from datetime import datetime
from pydantic import BaseModel, HttpUrl


class PushSubscriptionBase(BaseModel):
    endpoint: HttpUrl
    p256dh: str
    auth: str


class PushSubscriptionCreate(PushSubscriptionBase):
    pass


class PushSubscriptionResponse(PushSubscriptionBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
