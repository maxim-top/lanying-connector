import os
import openai
import requests
from flask import Flask, request
import logging
import json
import asyncio

logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__)
if os.environ.get("FLASK_DEBUG"):
    app.debug = True
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route("/messages", methods=["POST"])
def messages():
    text = request.get_data(as_text=True)
    data = json.loads(text)
    fromUserId = data['from']['uid']
    toUserId = data['to']['uid']
    type = data['type']
    ctype = data['ctype']
    myUserId = os.getenv('LANYING_USER_ID')
    logging.debug(data)
    if toUserId == myUserId and fromUserId != myUserId and type == 'CHAT' and ctype == 'TEXT':
        asyncio.run(queryAndSendMessage(data))
    resp = app.make_response('')
    return resp

async def queryAndSendMessage(data):
    appId = data['appId']
    fromUserId = data['from']['uid']
    toUserId = data['to']['uid']
    content = data['content']
    try:
        with open("preset.json", "r") as f:
            preset = json.load(f)
            preset['prompt'] = preset['prompt'].replace('{{LANYING_MESSAGE_CONTENT}}', content)
            response = openai.Completion.create(**preset)
            logging.debug(response)
            send_response = requests.post('https://s-1-3-api.maximtop.cn/message/send',
                                headers={'app_id': appId, 'access-token': os.getenv("LANYING_ADMIN_TOKEN")},
                                json={'type':1, 'from_user_id':toUserId,'targets':[fromUserId],'content_type':0, 'content': response.choices[0].text})
            logging.debug(send_response)
    except Exception as e:
        logging.error(e)
