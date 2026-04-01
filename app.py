from flask import Flask
import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import html

app = Flask(__name__)

def generate_email_reply():
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

    # Retrieves the last 5 messages from my inbox and pulls out the list of emails response
    results = service.users().messages().list(userId='me', maxResults=1).execute()
    messages = results.get('messages', [])

    # Loops through each email and retrieves:
    # 1. Who sent the message
    # The subject
    # Body of message
    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()

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

        Write a reply to this email:

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

    return {
        "sender": "Unknown",
        "subject": "No subject",
        "email_body": "No email found.",
        "reply": "No reply generated."
    }

@app.route("/")
def home():
    return """
    <h1>AI Email Assistant</h1>
    <form action="/generate">
        <button type="submit">Generate Reply for Latest Email</button>
    </form>
    """

@app.route("/generate")
def generate():
    print("DEBUG: /generate route hit")

    result = generate_email_reply()

    safe_sender = html.escape(result["sender"])
    safe_subject = html.escape(result["subject"])
    safe_email_body = html.escape(result["email_body"])
    safe_reply = html.escape(result["reply"])

    return f"""
    <h1>AI Email Assistant</h1>

    <h2>Latest Email</h2>
    <p><strong>From:</strong> {safe_sender}</p>
    <p><strong>Subject:</strong> {safe_subject}</p>

    <h3>Email Content:</h3>
    <pre style="white-space: pre-wrap; font-family: Arial; background-color: #f4f4f4; padding: 10px;">
{safe_email_body}
    </pre>

    <h2>AI Generated Reply</h2>
    <pre style="white-space: pre-wrap; font-family: Arial; background-color: #e8f0fe; padding: 10px;">
{safe_reply}
    </pre>

    <br>
    <a href="/">Go Back</a>
    """

if __name__ == "__main__":
    app.run(debug=True)