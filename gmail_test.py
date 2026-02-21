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
flow = InstalledAppFlow.from_client_secrets_file(
    'client_secret.json', SCOPES)

# Opens up a local web browser, allows you to log in and Google sends back a token (creds)
creds = flow.run_local_server(port=0)

# Creates a Python object that is able to talk to gmail for you
service = build('gmail', 'v1', credentials=creds)

# Retrieves the last 5 messages from my inbox and pulls out the list of emails response
results = service.users().messages().list(userId='me', maxResults=5).execute()
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

    print(response.choices[0].message.content)
