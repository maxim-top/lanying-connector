import openai
import time
import logging

historyList = []
expireSeconds = 600
maxPromptSize = 1500

def handle_chat_message(content, config):
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