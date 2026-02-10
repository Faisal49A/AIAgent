from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

flow = InstalledAppFlow.from_client_secrets_file(
    'client_secret.json', SCOPES)

creds = flow.run_local_server(port=0)

service = build('gmail', 'v1', credentials=creds)

results = service.users().messages().list(userId='me', maxResults=5).execute()
messages = results.get('messages', [])

print("Your latest emails:")
for msg in messages:
    print(msg['id'])




