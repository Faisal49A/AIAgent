from flask import Flask, request, render_template, jsonify
import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import html

app = Flask(__name__)

def generate_email_reply(message_id, tone):
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    import base64
    from dotenv import load_dotenv
    import os
    from openai import OpenAI

    def clean_email(text):
        lines = text.split("\n")
        clean_lines = []

        for line in lines:
            line = line.strip()

            if not line:
                continue
            if line.startswith(">"):
                continue
            if "unsubscribe" in line.lower():
                continue
            if "sent from my" in line.lower():
                continue
            if "wrote:" in line.lower():
                break  # stop at old thread

            clean_lines.append(line)

        return "\n".join(clean_lines)

    # Google API can only read emails not 'send' or 'delete'
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

    # loads the fle I downloaded from Google defined by the permissions in SCOPES
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "client_secret.json", SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    # Creates a Python object that is able to talk to gmail for you
    service = build('gmail', 'v1', credentials=creds)

    msg_data = service.users().messages().get(
        userId='me',
        id=message_id
    ).execute()


    # Separates the headers from the whole email
    payload = msg_data['payload']
    headers = payload['headers']

    # Gets subject and sender from the header section
    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "")
    sender = next((h['value'] for h in headers if h['name'] == 'From'), "")

    # Some emails have multiple parts, this grabs the first one.
    # If it doesnt have multiple parts then just grabs the body directly
    if 'parts' in payload:
        body = payload['parts'][0]['body'].get('data', '')
    else:
        body = payload['body'].get('data', '')

        # Converts encoded gmail text into bytes then uses base 64 to decode into readable text
    body = base64.urlsafe_b64decode(body.encode('ASCII')).decode('utf-8', errors='ignore')
    cleaned_body = clean_email(body)

    print("\nCLEANED EMAIL:")
    print(cleaned_body)
    print("\n-----------------\n")

        # Allows python to access your API key
        # Creates connection to OpenAI using my AIP key
    load_dotenv()
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Instruction to send to AI
    ai_prompt = f"""
    You are an assistant that writes polite, clear, professional email replies.

    Write a {tone} reply to this email:

    {cleaned_body}
    """
    # AI processes instruction and reads email content, then generates a reply
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": ai_prompt}]
    )

    return {
        "sender": sender,
        "subject": subject,
        "email_body": cleaned_body,
        "reply": response.choices[0].message.content
        }

def get_recent_emails():
    from googleapiclient.discovery import build

    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    service = build('gmail', 'v1', credentials=creds)

    results = service.users().messages().list(
        userId='me',
        maxResults=10
    ).execute()

    messages = results.get('messages', [])
    email_list = []

    for msg in messages:
        msg_data = service.users().messages().get(
            userId='me',
            id=msg['id']
        ).execute()

        headers = msg_data['payload']['headers']

        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject")
        sender = next((h['value'] for h in headers if h['name'] == 'From'), "Unknown Sender")

        email_list.append({
            "id": msg['id'],
            "subject": subject,
            "sender": sender
        })

    return email_list

@app.route("/")
def home():
    emails = get_recent_emails()
    return render_template("home.html", emails=emails)

@app.route("/api/emails")
def api_emails():
    emails = get_recent_emails()
    return jsonify({
        "emails": emails
    })

@app.route("/generate/<message_id>")
def generate(message_id):

    tone = request.args.get("tone", "professional")

    result = generate_email_reply(message_id,tone)

    sender = result["sender"]
    subject = result["subject"]
    email_body = result["email_body"]
    reply = result["reply"]

    return render_template(
        "result.html",
        sender=sender,
        subject=subject,
        email_body=email_body,
        reply=reply,
        tone=tone
    )

@app.route("/api/generate/<message_id>")
def api_generate(message_id):
    tone = request.args.get("tone", "professional")
    result = generate_email_reply(message_id, tone)
    return jsonify(result)

if __name__ == "__main__":
    app.run(debug=True)