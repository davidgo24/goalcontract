import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

try:
    from twilio.rest import Client
except ImportError:
    Client = None  

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
LOCAL_SMS = os.getenv("LOCAL_SMS", "false").lower() == "true"

def send_sms_twilio(to_number: str, body: str) -> Optional[str]:
    if not all([ACCOUNT_SID, AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
        raise ValueError("Twilio credentials not set in environment variables.")

    client = Client(ACCOUNT_SID, AUTH_TOKEN)
    try:
        message = client.messages.create(
            body=body,
            from_=TWILIO_PHONE_NUMBER,
            to=to_number,
        )
        print(f"✅ [Twilio] Sent to {to_number} | SID: {message.sid}")
        return message.sid
    except Exception as e:
        print(f"❌ [Twilio Error] Failed to send to {to_number}: {e}")
        return None

def send_sms_local(to_number: str, body: str) -> str:
    print(f"\n📱 [SIMULATED SMS to {to_number}]\n{body}\n")
    return "SIMULATED_SID"

def send_sms(to_number: str, body: str) -> Optional[str]:
    if LOCAL_SMS:
        return send_sms_local(to_number, body)
    else:
        return send_sms_twilio(to_number, body)
