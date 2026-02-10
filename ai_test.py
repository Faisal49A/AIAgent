from dotenv import load_dotenv
import os
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


email_text = """
Hi, I wanted to check if you are available for a meeting tomorrow at 10am.
Let me know, thanks!
"""

prompt = f"""
You are an assistant that writes polite, professional email replies.

Write a reply to this email:

{email_text}
"""

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": prompt}]
)

print(response.choices[0].message.content)
