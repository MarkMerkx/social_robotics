from openai import OpenAI
from src.api.conn import chat_gtp_connection

def guess(input, previous_guesses):
    api_key = chat_gtp_connection()
    client = OpenAI(api_key=api_key)

    prompt = (
        f"\n"
    )

    response = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="gpt-4",
        max_tokens=200,
        temperature=0.8
    )

    return response.choices[0].message.content.strip()
