import openai
import time
import logging
import lanying_connector
import json
import tiktoken
expireSeconds = 86400 * 3
maxUserHistoryLen = 20
MaxTotalTokens = 4000

def handle_chat_message(content, config):
    preset = config['preset']
    lcExt = {}
    try:
        ext = json.loads(config['ext'])
        lcExt = ext['lanying_connector']
        if lcExt['choose_preset']:
            preset = preset['presets'][lcExt['choose_preset']]
    except Exception as e:
        lcExt = {}
    if 'presets' in preset:
        del preset['presets']
    logging.debug(f"lanying-connector:ext={json.dumps(lcExt, ensure_ascii=False)}")
    isChatGPT = preset['model'].startswith("gpt-3.5")
    if isChatGPT:
        return handle_chat_message_chatgpt(content, config, preset, lcExt)
    else:
        return handle_chat_message_gpt3(content, config, preset, lcExt)

def handle_chat_message_gpt3(content, config, preset, lcExt):
    openai.api_key = config['openai_api_key']
    prompt = preset['prompt']
    now = int(time.time())
    history = {'time':now}
    fromUserId = config['from_user_id']
    toUserId = config['to_user_id']
    historyListKey = historyListGPT3Key(fromUserId, toUserId)
    redis = lanying_connector.getRedisConnection()
    historyText = loadHistory(redis, historyListKey, content, preset['prompt'], now, preset)
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

def handle_chat_message_chatgpt(content, config, preset, lcExt):
    openai.api_key = config['openai_api_key']
    messages = preset.get('messages',[])
    now = int(time.time())
    history = {'time':now}
    fromUserId = config['from_user_id']
    toUserId = config['to_user_id']
    historyListKey = historyListChatGPTKey(fromUserId, toUserId)
    redis = lanying_connector.getRedisConnection()
    if 'clear_history' in lcExt and lcExt['clear_history'] == True:
        removeAllHistory(redis, historyListKey)
    if 'add_history_list' in lcExt and lcExt['add_history_list']:
        customHistoryList = []
        for customHistory in lcExt['add_history_list']:
            if customHistory['role'] and customHistory['content']:
                customHistoryList.append({'role':customHistory['role'], 'content': customHistory['content']})
        addHistory(redis, historyListKey, {'list':customHistoryList, 'time':now})
    if 'need_reply' in lcExt and lcExt['need_reply'] == False:
        return ''
    if content == '!clear_history':
        removeAllHistory(redis, historyListKey)
        return 'history is clear'
    userHistoryList = loadHistoryChatGPT(redis, historyListKey, content, messages, now, preset)
    for userHistory in userHistoryList:
        logging.debug(f'userHistory:{userHistory}')
        messages.append(userHistory)
    messages.append({"role": "user", "content": content})
    preset['messages'] = messages
    calcMessagesTokens(messages, preset['model'])
    response = openai.ChatCompletion.create(**preset)
    logging.debug(f"openai response:{response}")
    reply = response.choices[0].message.content.strip()
    history['user'] = content
    history['assistant'] = reply
    history['uid'] = fromUserId
    addHistory(redis, historyListKey, history)
    return reply

def loadHistory(redis, historyListKey, content, prompt, now, preset):
    maxPromptSize = 3024 - preset.get('max_tokens', 1024)
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

def loadHistoryChatGPT(redis, historyListKey, content, messages, now, preset):
    completionTokens = preset.get('max_tokens', 1024)
    uidHistoryList = []
    model = preset['model']
    messagesSize = calcMessagesTokens(messages, model)
    askMessage = {"role": "user", "content": content}
    nowSize = calcMessageTokens(askMessage, model) + messagesSize
    if redis:
        for historyStr in getHistoryList(redis, historyListKey):
            history = json.loads(historyStr)
            if history['time'] < now - expireSeconds:
                removeHistory(redis, historyListKey, historyStr)
            uidHistoryList.append(history)
    res = []
    for history in reversed(uidHistoryList):
        if 'list' in history:
            nowHistoryList = history['list']
        else:
            userMessage = {'role':'user', 'content': history['user']}
            assistantMessage = {'role':'assistant', 'content': history['assistant']}
            nowHistoryList = [userMessage, assistantMessage]
        historySize = 0
        for nowHistory in nowHistoryList:
            historySize += calcMessageTokens(nowHistory, model)
        if nowSize + historySize + completionTokens < MaxTotalTokens:
            for nowHistory in reversed(nowHistoryList):
                res.append(nowHistory)
            nowSize += historySize
            logging.debug(f'now prompt size:{nowSize}')
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

def removeAllHistory(redis, historyListKey):
    if redis:
        redis.delete(historyListKey)

def calcMessagesTokens(messages, model):
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = 0
    for message in messages:
        num_tokens += 4
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += -1
    num_tokens += 2
    return num_tokens

def calcMessageTokens(message, model):
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = 0
    num_tokens += 4
    for key, value in message.items():
        num_tokens += len(encoding.encode(value))
        if key == "name":
            num_tokens += -1
    return num_tokens