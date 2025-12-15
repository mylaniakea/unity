from pywebpush import webpush
from fastapi import HTTPException
import json
import os

# VAPID keys configuration
VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "BP-PLACEHOLDER_PUBLIC_KEY_FOR_WEB_PUSH")
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "PLACEHOLDER_PRIVATE_KEY_FOR_WEB_PUSH")
VAPID_CLAIMS = {"sub": os.environ.get("VAPID_CLAIMS_SUB", "mailto:admin@homelab.intelligence")}

async def send_push_notification(subscription: dict, message: str):
    if not VAPID_PRIVATE_KEY or VAPID_PRIVATE_KEY == "PLACEHOLDER_PRIVATE_KEY_FOR_WEB_PUSH":
        print("VAPID_PRIVATE_KEY not set or is a placeholder. Skipping push notification.")
        return

    try:
        webpush(
            subscription_info=subscription,
            data=json.dumps({"message": message}),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims=VAPID_CLAIMS
        )
    except Exception as e:
        print(f"Error sending push notification: {e}")
        # Optionally, handle specific errors like subscription expired
        raise HTTPException(status_code=500, detail=f"Failed to send push notification: {e}")
