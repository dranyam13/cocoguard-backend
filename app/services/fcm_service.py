"""
Firebase Cloud Messaging (FCM) Push Notification Service

This service sends push notifications to mobile app users when:
- A dangerous pest (APW) is detected
- System-wide alerts need to be broadcast

Requirements:
- Firebase Admin SDK: pip install firebase-admin
- Service account key file (see PUSH_NOTIFICATION_SETUP.md)
"""

import os
import json
import httpx
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

# Try to import firebase_admin, but make it optional
try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    print("[FCM] firebase-admin not installed. Run: pip install firebase-admin")

# Path to the Firebase service account key file
FIREBASE_CREDS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "firebase-service-account.json"
)

# FCM Topic for broadcast notifications
PEST_ALERTS_TOPIC = "pest_alerts"

# Flag to track if Firebase is initialized
_firebase_initialized = False


def init_firebase():
    """Initialize Firebase Admin SDK if not already initialized"""
    global _firebase_initialized
    
    if not FIREBASE_AVAILABLE:
        print("[FCM] Firebase Admin SDK not available. Push notifications disabled.")
        return False
    
    if _firebase_initialized:
        return True
    
    try:
        if os.path.exists(FIREBASE_CREDS_PATH):
            cred = credentials.Certificate(FIREBASE_CREDS_PATH)
            firebase_admin.initialize_app(cred)
            _firebase_initialized = True
            print(f"[FCM] Firebase initialized with credentials from {FIREBASE_CREDS_PATH}")
            return True
        else:
            # Try environment variable
            creds_json = os.environ.get('FIREBASE_CREDENTIALS')
            if creds_json:
                cred_dict = json.loads(creds_json)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
                _firebase_initialized = True
                print("[FCM] Firebase initialized with credentials from environment variable")
                return True
            else:
                print(f"[FCM] Firebase credentials not found at {FIREBASE_CREDS_PATH}")
                print("[FCM] Push notifications are disabled until Firebase is configured.")
                return False
    except Exception as e:
        print(f"[FCM] Failed to initialize Firebase: {e}")
        return False


def send_pest_alert_notification(
    pest_type: str,
    location_text: Optional[str] = None,
    scan_id: Optional[int] = None,
    fcm_tokens: Optional[List[str]] = None,
    send_to_topic: bool = True
) -> Dict[str, Any]:
    """
    Send a push notification for a dangerous pest detection.
    
    Args:
        pest_type: Type of pest detected (e.g., "APW Adult")
        location_text: Where the pest was detected
        scan_id: ID of the scan that detected the pest
        fcm_tokens: Optional list of specific device tokens to notify
        send_to_topic: Whether to also send to the pest_alerts topic
        
    Returns:
        Dict with success status and details
    """
    if not init_firebase():
        return {
            "success": False,
            "message": "Firebase not initialized. Push notifications disabled.",
            "sent_count": 0
        }
    
    # Build notification content
    title = "⚠️ Mapanganib na Peste ang Natuklasan!"
    body = (
        f"Ang {pest_type} ay natuklasan sa lugar na: "
        f"{location_text or 'Hindi matukoy ang lokasyon'}. "
        "Mangyaring suriin ang inyong mga puno ng niyog."
    )
    
    # Notification data payload (for handling in app)
    data = {
        "type": "pest_alert",
        "pest_type": pest_type,
        "location_text": location_text or "",
        "scan_id": str(scan_id) if scan_id else "",
        "is_critical": "true" if "APW" in pest_type else "false",
        "timestamp": datetime.now().isoformat(),
        "click_action": "FLUTTER_NOTIFICATION_CLICK"
    }
    
    # Android notification configuration for heads-up display
    android_config = messaging.AndroidConfig(
        priority='high',
        notification=messaging.AndroidNotification(
            title=title,
            body=body,
            icon='ic_launcher',
            color='#DC3545' if 'APW' in pest_type else '#2D7A3E',
            channel_id='pest_alerts_channel',
            priority='max',
            visibility='public',
            notification_count=1,
            default_vibrate_timings=True,  # Use default vibration
        ),
        ttl=timedelta(hours=1)  # 1 hour TTL
    )
    
    # iOS/APNs configuration
    apns_config = messaging.APNSConfig(
        headers={
            'apns-priority': '10',
            'apns-push-type': 'alert'
        },
        payload=messaging.APNSPayload(
            aps=messaging.Aps(
                alert=messaging.ApsAlert(
                    title=title,
                    body=body,
                ),
                badge=1,
                sound=messaging.CriticalSound(
                    name='default',
                    critical=True,
                    volume=1.0
                ),
                mutable_content=True,
            )
        )
    )
    
    results = {
        "success": True,
        "topic_sent": False,
        "tokens_sent": 0,
        "tokens_failed": 0,
        "details": []
    }
    
    # Send to topic (broadcast to all subscribers)
    if send_to_topic:
        try:
            topic_message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data,
                android=android_config,
                apns=apns_config,
                topic=PEST_ALERTS_TOPIC
            )
            response = messaging.send(topic_message)
            results["topic_sent"] = True
            results["details"].append(f"Topic message sent: {response}")
            print(f"[FCM] ✅ Sent to topic '{PEST_ALERTS_TOPIC}': {response}")
        except Exception as e:
            results["details"].append(f"Topic send failed: {str(e)}")
            print(f"[FCM] ❌ Failed to send to topic: {e}")
    
    # Send to specific device tokens
    if fcm_tokens:
        # Filter out empty/None tokens
        valid_tokens = [t for t in fcm_tokens if t]
        
        if valid_tokens:
            # Use multicast for multiple tokens (max 500 per call)
            for i in range(0, len(valid_tokens), 500):
                batch_tokens = valid_tokens[i:i+500]
                
                multicast_message = messaging.MulticastMessage(
                    notification=messaging.Notification(
                        title=title,
                        body=body,
                    ),
                    data=data,
                    android=android_config,
                    apns=apns_config,
                    tokens=batch_tokens
                )
                
                try:
                    response = messaging.send_each_for_multicast(multicast_message)
                    results["tokens_sent"] += response.success_count
                    results["tokens_failed"] += response.failure_count
                    
                    print(f"[FCM] ✅ Multicast: {response.success_count} success, "
                          f"{response.failure_count} failed")
                    
                    # Log failed tokens for cleanup
                    if response.failure_count > 0:
                        for idx, resp in enumerate(response.responses):
                            if not resp.success:
                                print(f"[FCM] ❌ Failed token: {batch_tokens[idx][:20]}... "
                                      f"Error: {resp.exception}")
                                
                except Exception as e:
                    results["details"].append(f"Multicast failed: {str(e)}")
                    print(f"[FCM] ❌ Multicast send failed: {e}")
    
    # Calculate overall success
    results["message"] = (
        f"Sent to topic: {results['topic_sent']}, "
        f"Tokens: {results['tokens_sent']} success, {results['tokens_failed']} failed"
    )
    
    return results


def send_notification_to_token(
    token: str,
    title: str,
    body: str,
    data: Optional[Dict[str, str]] = None
) -> bool:
    """
    Send a notification to a specific device token.
    
    Args:
        token: FCM device token
        title: Notification title
        body: Notification body
        data: Optional data payload
        
    Returns:
        True if sent successfully, False otherwise
    """
    if not init_firebase():
        return False
    
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
            token=token,
        )
        response = messaging.send(message)
        print(f"[FCM] ✅ Sent to token: {response}")
        return True
    except Exception as e:
        print(f"[FCM] ❌ Failed to send to token: {e}")
        return False


def send_topic_notification(
    topic: str,
    title: str,
    body: str,
    data: Optional[Dict[str, str]] = None
) -> bool:
    """
    Send a notification to all subscribers of a topic.
    
    Args:
        topic: Topic name (e.g., "pest_alerts")
        title: Notification title
        body: Notification body
        data: Optional data payload
        
    Returns:
        True if sent successfully, False otherwise
    """
    if not init_firebase():
        return False
    
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
            topic=topic,
        )
        response = messaging.send(message)
        print(f"[FCM] ✅ Sent to topic '{topic}': {response}")
        return True
    except Exception as e:
        print(f"[FCM] ❌ Failed to send to topic: {e}")
        return False
