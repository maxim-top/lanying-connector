import openai

def handle_chat_message(content, config):
    openai.api_key = config['openai_api_key']
    preset = config['preset']
    prompt = preset['prompt']
    if prompt.find('{{LANYING_MESSAGE_CONTENT}}') > 0:
        preset['prompt'] = prompt.replace('{{LANYING_MESSAGE_CONTENT}}', content)
    else:
        if len(preset['stop']) == 2:
            preset['prompt'] = prompt + preset['stop'][0] + content + "\n" + preset['stop'][1]
        else:
            preset['prompt'] = prompt + "Human:" + content + "\n" + "AI:"
    response = openai.Completion.create(**preset)
    return response.choices[0].text.strip()
