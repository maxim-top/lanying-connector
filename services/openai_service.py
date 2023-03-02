import openai
import time
import logging

historyList = []
historyListChatGPT = []
expireSeconds = 600
maxPromptSize = 1500

def handle_chat_message(content, config):
    preset = config['preset']
    isChatGPT = preset['model'].startswith("gpt-3.5")
    if isChatGPT:
        return handle_chat_message_chatgpt(content, config)
    else:
        return handle_chat_message_gpt3(content, config)

def handle_chat_message_gpt3(content, config):
    openai.api_key = config['openai_api_key']
    preset = config['preset']
    prompt = preset['prompt']
    now = int(time.time())
    history = {'time':now}
    fromUserId = config['from_user_id']
    historyText = loadHistory(fromUserId, content, preset['prompt'], now)
    logging.debug(f'historyText:{historyText}')
    if prompt.find('{{LANYING_MESSAGE_CONTENT}}') > 0:
        preset['prompt'] = prompt.replace('{{LANYING_MESSAGE_CONTENT}}', content)
    else:
        if len(preset['stop']) == 2:
            stop0 = preset['stop'][0].replace(' ', '')
            stop1 = preset['stop'][1].replace(' ', '')
            history['text'] = stop0 + content + "\n" + stop1
            preset['prompt'] = prompt + "\n" + historyText + stop0 + content + "\n" + stop1
        else:
            history['text'] = "Human:" + content + "\n" + "AI:"
            preset['prompt'] = prompt + "\n"  + historyText + "Human:" + content + "\n" + "AI:"
    response = openai.Completion.create(**preset)
    reply = response.choices[0].text.strip()
    if 'text' in history:
        history['text'] = history['text'] + reply + "\n\n"
        history['uid'] = fromUserId
        historyList.append(history)
    return reply

def handle_chat_message_chatgpt(content, config):
    openai.api_key = config['openai_api_key']
    preset = config['preset']
    messages = preset['messages']
    now = int(time.time())
    history = {'time':now}
    fromUserId = config['from_user_id']
    userHistoryList = loadHistoryChatGPT(fromUserId, content, messages, now)
    logging.debug(f'userHistoryList:{userHistoryList}')
    messages.extend(userHistoryList)
    messages.append({"role": "user", "content": content})
    preset['messages'] = messages
    response = openai.ChatCompletion.create(**preset)
    logging.debug(f"openai response:{response}")
    reply = response.choices[0].message.content.strip()
    history['user'] = content
    history['assistant'] = reply
    history['uid'] = fromUserId
    historyListChatGPT.append(history)
    return reply

def loadHistory(uid, content, prompt, now):
    uidHistoryList = []
    nowSize = len(content) + len(prompt)
    for history in historyList[:]:
        if history['time'] < now - expireSeconds:
            historyList.remove(history)
        elif history['uid'] == uid:
            uidHistoryList.append(history)
    res = ""
    for history in reversed(uidHistoryList):
        if res == "" or nowSize + len(history['text']) < maxPromptSize:
            res = history['text'] + res
            nowSize += len(history['text'])
            logging.debug(f'resLen:{len(res)}, nowSize:{nowSize}')
        else:
            break
    return res

def loadHistoryChatGPT(uid, content, messages, now):
    uidHistoryList = []
    messagesSize = 0
    for message in messages:
        messagesSize += len('user') + len(message['user']) + len('assistant') + len(message['assistant'])
    nowSize = len(content) + messagesSize
    for history in historyListChatGPT[:]:
        if history['time'] < now - expireSeconds:
            historyListChatGPT.remove(history)
        elif history['uid'] == uid:
            uidHistoryList.append(history)
    res = []
    for history in reversed(uidHistoryList):
        historySize = len('user') + len(history['user']) + len('assistant') + len(history['assistant'])
        if len(res) == 0 or nowSize + historySize < maxPromptSize:
            res.append({'role':'assistant', 'content': history['assistant']})
            res.append({'role':'user', 'content': history['user']})
            nowSize += historySize
            logging.debug(f'resLen:{len(res)}, nowSize:{nowSize}')
        else:
            break
    return reversed(res)