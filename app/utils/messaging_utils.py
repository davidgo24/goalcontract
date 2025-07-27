import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')

twilio_client = None

if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    try:
        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        print("Twilio client initialized")
    except Exception as e:
        print(f"Error initializing Twilio client: {e}")
        twilio_client = None
else:
    print("WARNING: Twilio credentials not set. SMS functionality disabled.")

def send_sms(to_number: str, body: str):
    """Send an SMS using Twilio. Numbers should be in E.164 format or raw 10-digit US."""
    if not to_number.startswith('+'):
        cleaned_number = to_number.replace('-', '').replace(' ', '').strip()
        if len(cleaned_number) == 10 and cleaned_number.isdigit():
            to_number = f"+1{cleaned_number}"
        else:
            print(f"SMS not sent: Invalid number format: '{to_number}'")
            return None

    if not twilio_client or not TWILIO_PHONE_NUMBER:
        print(f"SMS not sent: Missing client or phone number. To: {to_number}, Body: {body}")
        return None

    try:
        message = twilio_client.messages.create(
            to=to_number,
            from_=TWILIO_PHONE_NUMBER,
            body=body
        )
        print(f"✅ SMS sent to {to_number}. SID: {message.sid}")
        return message.sid
    except Exception as e:
        print(f"Failed to send SMS to {to_number}: {e}")
        return None
