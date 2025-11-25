from openai import OpenAI
from API_KEYS import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

response = client.responses.create(
    #model="gpt-5.1",
    model="gpt-5-nano",
    input="Write a short bedtime story about a unicorn."
)

print(response.output_text)