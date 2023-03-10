import openai
import time
import logging
import lanying_connector
import json
expireSeconds = 86400 * 3
maxPromptSize = 2000
maxUserHistoryLen = 20

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
    toUserId = config['to_user_id']
    historyListKey = historyListGPT3Key(fromUserId, toUserId)
    redis = lanying_connector.getRedisConnection()
    historyText = loadHistory(redis, historyListKey, content, preset['prompt'], now)
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
        addHistory(redis, historyListKey, history)
    return reply

def handle_chat_message_chatgpt(content, config):
    openai.api_key = config['openai_api_key']
    preset = config['preset']
    messages = preset.get('messages',[])
    now = int(time.time())
    history = {'time':now}
    fromUserId = config['from_user_id']
    toUserId = config['to_user_id']
    historyListKey = historyListChatGPTKey(fromUserId, toUserId)
    redis = lanying_connector.getRedisConnection()
    userHistoryList = loadHistoryChatGPT(redis, historyListKey, content, messages, now)
    for userHistory in userHistoryList:
        logging.debug(f'userHistory:{userHistory}')
        messages.append(userHistory)
    messages.append({"role": "user", "content": content})
    preset['messages'] = messages
    response = openai.ChatCompletion.create(**preset)
    logging.debug(f"openai response:{response}")
    reply = response.choices[0].message.content.strip()
    history['user'] = content
    history['assistant'] = reply
    history['uid'] = fromUserId
    addHistory(redis, historyListKey, history)
    return reply

def loadHistory(redis, historyListKey, content, prompt, now):
    uidHistoryList = []
    nowSize = len(content) + len(prompt)
    if redis:
        for historyStr in getHistoryList(redis, historyListKey):
            history = json.loads(historyStr)
            if history['time'] < now - expireSeconds:
                removeHistory(redis, historyListKey, historyStr)
            uidHistoryList.append(history)
    res = ""
    for history in reversed(uidHistoryList):
        if nowSize + len(history['text']) < maxPromptSize:
            res = history['text'] + res
            nowSize += len(history['text'])
            logging.debug(f'resLen:{len(res)}, nowSize:{nowSize}')
        else:
            break
    return res

def loadHistoryChatGPT(redis, historyListKey, content, messages, now):
    uidHistoryList = []
    messagesSize = 0
    for message in messages:
        messagesSize += len(message['role']) + len(message['content'])
    nowSize = len(content) + messagesSize
    if redis:
        for historyStr in getHistoryList(redis, historyListKey):
            history = json.loads(historyStr)
            if history['time'] < now - expireSeconds:
                removeHistory(redis, historyListKey, historyStr)
            uidHistoryList.append(history)
    res = []
    for history in reversed(uidHistoryList):
        historySize = len(history['user']) + len(history['assistant'])
        if nowSize + historySize < maxPromptSize:
            res.append({'role':'assistant', 'content': history['assistant']})
            res.append({'role':'user', 'content': history['user']})
            nowSize += historySize
            logging.debug(f'resLen:{len(res)}, nowSize:{nowSize}')
        else:
            break
    return reversed(res)

def historyListChatGPTKey(fromUserId, toUserId):
    return "lanying:connector:history:list:chatGPT:" + fromUserId + ":" + toUserId

def historyListGPT3Key(fromUserId, toUserId):
    return "lanying:connector:history:list:gpt3" + fromUserId + ":" + toUserId

def addHistory(redis, historyListKey, history):
    if redis:
        Count = redis.rpush(historyListKey, json.dumps(history))
        redis.expire(historyListKey, expireSeconds)
        if Count > maxUserHistoryLen:
            redis.lpop(historyListKey)

def getHistoryList(redis, historyListKey):
    if redis:
        return redis.lrange(historyListKey, 0, -1)
    return []

def removeHistory(redis, historyListKey, historyStr):
    if redis:
        redis.lrem(historyListKey, 1, historyStr)
