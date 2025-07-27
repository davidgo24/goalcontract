import logging
from datetime import datetime  
from resend import Emails

def format_subject(message_type: str) -> str:
    today = datetime.now().strftime("%A %B %d, %Y")
    return f"{message_type} {today}"

def send_email(to_email: str, message_type: str, message_body: str, buddy_name: str) -> None:
    subject = format_subject(message_type)

    try:
        response = Emails.send({
            "from": f"{buddy_name} <goalcontract@bizzytext.com>",            
            "to": [to_email],
            "subject": subject,
            "html": f"<pre style='font-size: 16px'>{message_body}</pre>"
        })

        logging.info(f"📧 Resend email response: {response}")

        if not response or not isinstance(response, dict) or not response.get("id"):
            raise ValueError("❌ Resend API did not return a valid response or ID.")

        logging.info(f"✅ Email successfully sent to {to_email} with ID: {response['id']}")

    except Exception as e:
        logging.error(f"❌ Email sending failed: {e}", exc_info=True)
        raise
