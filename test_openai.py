from openai import OpenAI

# load openai key from file
with open('openai_key.txt', 'r') as f:
    api_key = f.read().strip()

oai_client = OpenAI(api_key = api_key)

response = oai_client.chat.completions.create(
    model="gpt-3.5-turbo-0125",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello"},
    ],
    max_tokens = 150
)

print(response.choices[0].message.content)