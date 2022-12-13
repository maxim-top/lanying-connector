import openai

def handle_chat_message(content, config):
    openai.api_key = config['openai_api_key']
    preset = config['preset']
    prompt = preset['prompt']
    preset['prompt'] = prompt.replace('{{LANYING_MESSAGE_CONTENT}}', content)
    response = openai.Completion.create(**preset)
    return response.choices[0].text.strip()
