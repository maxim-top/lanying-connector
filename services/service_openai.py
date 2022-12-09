import openai
import json
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

def handle_chat_message(content):
    with open("configs/openai.json", "r") as f:
        preset = json.load(f)
        preset['prompt'] = preset['prompt'].replace('{{LANYING_MESSAGE_CONTENT}}', content)
        response = openai.Completion.create(**preset)
        return response.choices[0].text
