import openai
import json
import os

with open("configs/openai.json", "r") as f:
    config = json.load(f)
    if(config['openai_api_key'] != ""):
        openai.api_key = config['openai_api_key']
    else:
        openai.api_key = os.getenv("OPENAI_API_KEY")
    preset = config['preset']
    prompt = preset['prompt']

def handle_chat_message(content):
    preset['prompt'] = prompt.replace('{{LANYING_MESSAGE_CONTENT}}', content)
    response = openai.Completion.create(**preset)
    return response.choices[0].text
