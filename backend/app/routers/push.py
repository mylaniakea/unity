from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app import models
from app.schemas.notifications import *
from app.services.push_notifications import send_push_notification, VAPID_PUBLIC_KEY

router = APIRouter(
    prefix="/push",
    tags=["push"],
    responses={404: {"description": "Not found"}},
)

@router.get("/vapid-public-key")
def get_vapid_public_key():
    return {"publicKey": VAPID_PUBLIC_KEY}

@router.post("/subscribe", response_model=PushSubscriptionResponse)
def subscribe_push(subscription_in: PushSubscriptionCreate, db: Session = Depends(get_db)):
    # Check if subscription already exists
    existing_subscription = db.query(models.PushSubscription).filter(
        models.PushSubscription.endpoint == subscription_in.endpoint
    ).first()

    if existing_subscription:
        return existing_subscription # Return existing subscription if found

    db_subscription = models.PushSubscription(
        endpoint=subscription_in.endpoint,
        p256dh=subscription_in.p256dh,
        auth=subscription_in.auth
    )
    db.add(db_subscription)
    db.commit()
    db.refresh(db_subscription)
    return db_subscription

@router.post("/unsubscribe", status_code=204)
def unsubscribe_push(subscription_in: PushSubscriptionCreate, db: Session = Depends(get_db)):
    subscription = db.query(models.PushSubscription).filter(
        models.PushSubscription.endpoint == subscription_in.endpoint
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    db.delete(subscription)
    db.commit()
    return {"message": "Subscription removed"}
