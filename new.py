import os
import logging
from flask import Flask, request, jsonify
from openai import AzureOpenAI
import requests
from dotenv import load_dotenv

from whatsapp_cta import send_cta_url

from whatsapp_list import send_interactive_list

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
user_state = {}
# Initialize Flask app
app = Flask(__name__)

# WhatsApp Configuration
WHATSAPP_TOKEN = os.getenv('WHATSAPP_TOKEN')
WHATSAPP_PHONE_NUMBER_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID', '863358323523381')
VERIFY_TOKEN = os.getenv('VERIFY_TOKEN', 'your_verify_token_here')

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT', 'https://baarilabs.openai.azure.com/')
AZURE_OPENAI_API_KEY = os.getenv('AZURE_OPENAI_API_KEY')
AZURE_OPENAI_DEPLOYMENT = os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-4o')
AZURE_OPENAI_API_VERSION = os.getenv('AZURE_OPENAI_API_VERSION', '2024-12-01-preview')

# Initialize Azure OpenAI client (lazy initialization to avoid startup errors)
client = None

def get_openai_client():
    """Get or create the Azure OpenAI client"""
    global client
    if client is None:
        client = AzureOpenAI(
            api_version=AZURE_OPENAI_API_VERSION,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
        )
    return client


def generate_ai_response(user_message):
    """Generate a response using Azure OpenAI"""
    try:
        ai_client = get_openai_client()
        response = ai_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful WhatsApp assistant. Provide concise, friendly, and helpful responses.",
                },
                {
                    "role": "user",
                    "content": user_message,
                }
            ],
            max_tokens=500,
            temperature=0.7,
            top_p=1.0,
            model=AZURE_OPENAI_DEPLOYMENT
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error generating AI response: {e}")
        return "Sorry, I encountered an error processing your message. Please try again."


def send_whatsapp_message(to_phone_number, message_text):
    """Send a message via WhatsApp Cloud API"""
    url = f"https://graph.facebook.com/v22.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    
    headers = {
        'Authorization': f'Bearer {WHATSAPP_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_phone_number,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": message_text
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        logger.info(f"Message sent successfully to {to_phone_number}")
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending WhatsApp message: {e}")
        if hasattr(e.response, 'text'):
            logger.error(f"Response: {e.response.text}")
        raise

def send_cta_document_button(to_phone_number):
    """
    Sends a CTA URL message with a document header (PDF with custom filename)
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
            "type": "cta_url",
            "header": {
                "type": "document",
                "document": {
                    "link": "https://www.rgpv.ac.in/UC/frm_download_file.aspx?Filepath=CDN/PubContent/Scheme/VIII%20CSE120325054719.pdf",
                    "filename": "RGPV_CSE_8th_Sem_Syllabus.pdf"
                }
            },
            "body": {
                "text": "Syllabus for 8th Semester CSE (RGPV)"
            },
            "action": {
                "name": "cta_url",
                "parameters": {
                    "display_text": "View Scheme",
                    "url": "https://www.rgpv.ac.in/uni/frm_viewscheme.aspx"
                }
            }
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        logger.info("CTA document button sent successfully")
        return response.json()

    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending CTA document button: {e}")
        if e.response is not None:
            logger.error(e.response.text)
        raise


@app.route('/webhook', methods=['GET'])
def verify_webhook():
    """Verify webhook for WhatsApp"""
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    if mode == 'subscribe' and token == VERIFY_TOKEN:
        logger.info("Webhook verified successfully")
        return challenge, 200
    else:
        logger.warning("Webhook verification failed")
        return jsonify({"error": "Verification failed"}), 403


@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        logger.info(f"Received webhook data: {data}")

        if data.get('object') != 'whatsapp_business_account':
            return jsonify({"status": "ignored"}), 200

        for entry in data.get('entry', []):
            for change in entry.get('changes', []):
                value = change.get('value', {})
                messages = value.get('messages', [])

                for message in messages:
                    from_number = message.get('from')
                    message_type = message.get('type')

                    # =====================================
                    # ✅ 1. HANDLE INTERACTIVE LIST REPLY
                    # =====================================
                    if message_type == "interactive":
                        interactive = message.get("interactive", {})

                        if interactive.get("type") == "list_reply":
                            selected_id = interactive["list_reply"]["id"]

                            # 🔹 OPTION: SIMPLIFIIQ
                            if selected_id == "simplifiiq":
                                send_cta_url(
                                    to_phone_number=from_number,
                                    body_text="Explore Simplifiiq – AI-Powered Business Solutions",
                                    button_text="Visit Website",
                                    button_url="https://www.simplifiiq.com/",
                                    header_type="image",
                                    header_value="https://media.licdn.com/dms/image/v2/D4D16AQHWtW1MlWLbwg/profile-displaybackgroundimage-shrink_200_800/B4DZlhYHUJGwAY-/0/1758275336739?e=2147483647&v=beta&t=GYTC2gKGsqDSuhGUWUf2mFqBJZMjD7T-MKZR9I9A-P0",
                                    footer_text="Powered by Simplifiiq"
                                )

                            # 🔹 OPTION: SYLLABUS
                            elif selected_id == "syllabus":
                                send_cta_url(
                                    to_phone_number=from_number,
                                    body_text="Here is the syllabus for 8th Semester CSE (RGPV)",
                                    button_text="View Scheme",
                                    button_url="https://www.rgpv.ac.in/uni/frm_viewscheme.aspx",
                                    header_type="document",
                                    header_value="https://www.rgpv.ac.in/UC/frm_download_file.aspx?Filepath=CDN/PubContent/Scheme/VIII%20CSE120325054719.pdf",
                                    filename="RGPV_CSE_8th_Sem_Syllabus.pdf",
                                    footer_text="Official RGPV syllabus"
                                )

                        continue   # 🔴 VERY IMPORTANT

                    # =====================================
                    # ✅ 2. HANDLE TEXT MESSAGES
                    # =====================================
                    if message_type != "text":
                        continue

                    user_message = message.get('text', {}).get('body', '').strip().lower()
                    logger.info(f"Message from {from_number}: {user_message}")

                    # MENU → SEND LIST
                    if user_message == "menu":
                        sections = [
                            {
                                "title": "Choose an option",
                                "rows": [
                                    {
                                        "id": "simplifiiq",
                                        "title": "Simplifiiq",
                                        "description": "AI-Powered Business Solutions"
                                    },
                                    {
                                        "id": "syllabus",
                                        "title": "Syllabus",
                                        "description": "View RGPV syllabus"
                                    }
                                ]
                            }
                        ]

                        send_interactive_list(
                            to_phone_number=from_number,
                            header_text="Main Menu",
                            body_text="Please select one option:",
                            footer_text="Tap Select to continue",
                            button_text="Select",
                            sections=sections
                        )
                        continue

                    # DEFAULT → AI
                    ai_response = generate_ai_response(user_message)
                    send_whatsapp_message(from_number, ai_response)

        return jsonify({"status": "success"}), 200

    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500




@app.route('/test', methods=['POST'])
def test_send_message():
    """Test endpoint to send a message"""
    data = request.get_json()
    phone_number = data.get('phone_number')
    message = data.get('message')
    
    if not phone_number or not message:
        return jsonify({"error": "phone_number and message are required"}), 400
    
    try:
        result = send_whatsapp_message(phone_number, message)
        return jsonify({"status": "success", "result": result}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "WhatsApp AI Bot"}), 200


if __name__ == '__main__':
    # Verify environment variables are set
    if not WHATSAPP_TOKEN:
        logger.error("WHATSAPP_TOKEN not set!")
    if not AZURE_OPENAI_API_KEY:
        logger.error("AZURE_OPENAI_API_KEY not set!")
    
    # Run the Flask app
    port = int(os.getenv('PORT', 5000))
    logger.info(f"Starting WhatsApp AI Bot on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

