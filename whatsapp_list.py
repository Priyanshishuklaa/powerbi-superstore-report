import os
import requests
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")


def send_interactive_list(
    to_phone_number: str,
    header_text: str,
    body_text: str,
    footer_text: str,
    button_text: str,
    sections: list
):
    """
    Generic WhatsApp Interactive List sender

    sections format:
    [
        {
            "title": "Section Title",
            "rows": [
                {
                    "id": "row_id_1",
                    "title": "Row Title",
                    "description": "Optional description"
                }
            ]
        }
    ]
    """

    url = f"https://graph.facebook.com/v24.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_phone_number,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {
                "type": "text",
                "text": header_text
            },
            "body": {
                "text": body_text
            },
            "footer": {
                "text": footer_text
            },
            "action": {
                "button": button_text,
                "sections": sections
            }
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        logger.info("Interactive list sent successfully")
        return response.json()

    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending interactive list: {e}")
        if e.response:
            logger.error(e.response.text)
        raise
