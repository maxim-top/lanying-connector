import os
from flask import Flask, request, render_template
import requests
import logging
import json
from concurrent.futures import ThreadPoolExecutor
import importlib
import sys

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
executor = ThreadPoolExecutor(2)
msgReceivedCnt = 0
msgSentCnt = 0
service = os.getenv('LANYING_CONNECTOR_SERVICE')
sys.path.append("services")
service_module = importlib.import_module(f"service_{service}")
app = Flask(__name__)
if os.environ.get("FLASK_DEBUG"):
    app.debug = True

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", msgReceivedCnt=msgReceivedCnt, msgSentCnt=msgSentCnt, service=service)

@app.route("/messages", methods=["POST"])
def messages():
    global msgReceivedCnt
    msgReceivedCnt += 1
    text = request.get_data(as_text=True)
    data = json.loads(text)
    logging.debug(data)
    fromUserId = data['from']['uid']
    toUserId = data['to']['uid']
    type = data['type']
    ctype = data['ctype']
    myUserId = os.getenv('LANYING_USER_ID')
    if toUserId == myUserId and fromUserId != myUserId and type == 'CHAT' and ctype == 'TEXT':
        executor.submit(queryAndSendMessage, data)
    resp = app.make_response('')
    return resp

def queryAndSendMessage(data):
    global msgSentCnt
    global service
    appId = data['appId']
    fromUserId = data['from']['uid']
    toUserId = data['to']['uid']
    content = data['content']
    try:
        responseText = service_module.handle_chat_message(content)
        logging.debug(responseText)
        sendMessage(appId, fromUserId, toUserId, responseText)
        msgSentCnt+=1
    except Exception as e:
        logging.error(e)
        sendMessage(appId, fromUserId, toUserId, os.getenv("LANYING_CONNECTOR_404_REPLY_MESSAGE", "抱歉，因为某些无法说明的原因，我暂时无法回答你的问题。"))
        msgSentCnt+=1

def sendMessage(appId, fromUserId, toUserId, content):
    sendResponse = requests.post('https://s-1-3-api.maximtop.cn/message/send',
                                headers={'app_id': appId, 'access-token': os.getenv("LANYING_ADMIN_TOKEN")},
                                json={'type':1, 'from_user_id':toUserId,'targets':[fromUserId],'content_type':0, 'content': content})
    logging.debug(sendResponse)