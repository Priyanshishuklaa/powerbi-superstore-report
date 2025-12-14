import requests
import logging
import os
from dotenv import load_dotenv

load_dotenv() 
logger = logging.getLogger(__name__)

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")


def send_cta_url(
    to_phone_number: str,
    body_text: str,
    button_text: str,
    button_url: str,
    header_type: str = None,
    header_value: str = None,
    filename: str = None,
    footer_text: str = None
):
    """
    Generic CTA URL sender (boilerplate)

    header_type: image | document | text | video | None
    header_value:
        - image/video/document → public URL
        - text → header text
    filename: optional (only for document)
    """

    url = f"https://graph.facebook.com/v24.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    interactive = {
        "type": "cta_url",
        "body": {"text": body_text},
        "action": {
            "name": "cta_url",
            "parameters": {
                "display_text": button_text[:20],
                "url": button_url
            }
        }
    }

    # 🔹 Header (optional)
    if header_type:
        if header_type == "text":
            interactive["header"] = {
                "type": "text",
                "text": header_value[:60]
            }

        elif header_type in ("image", "video"):
            interactive["header"] = {
                "type": header_type,
                header_type: {"link": header_value}
            }

        elif header_type == "document":
            doc = {"link": header_value}
            if filename:
                doc["filename"] = filename

            interactive["header"] = {
                "type": "document",
                "document": doc
            }

    # 🔹 Footer (optional)
    if footer_text:
        interactive["footer"] = {"text": footer_text[:60]}

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_phone_number,
        "type": "interactive",
        "interactive": interactive
    }

    try:
        resp = requests.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        logger.info("CTA sent successfully")
        return resp.json()

    except requests.exceptions.RequestException as e:
        logger.error(f"CTA send failed: {e}")
        if e.response:
            logger.error(e.response.text)
        raise
