import os
from flask import Flask, request, render_template
import requests
import logging
import json
from concurrent.futures import ThreadPoolExecutor
import importlib
import sys
import lanying_config
import copy

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
executor = ThreadPoolExecutor(2)
msgReceivedCnt = 0
msgSentCnt = 0
sys.path.append("services")
lanying_config.init()
app = Flask(__name__)
if os.environ.get("FLASK_DEBUG"):
    app.debug = True

@app.route("/", methods=["GET"])
def index():
    service = lanying_config.get_lanying_connector_service('')
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
    appId = data['appId']
    myUserId = lanying_config.get_lanying_user_id(appId)
    logging.debug(f'lanying_user_id:{myUserId}')
    if myUserId != None and toUserId == myUserId and fromUserId != myUserId and type == 'CHAT' and ctype == 'TEXT':
        executor.submit(queryAndSendMessage, data)
    resp = app.make_response('')
    return resp

def queryAndSendMessage(data):
    global msgSentCnt
    appId = data['appId']
    fromUserId = data['from']['uid']
    toUserId = data['to']['uid']
    content = data['content']
    try:
        service = lanying_config.get_lanying_connector_service(appId)
        if service:
            service_module = importlib.import_module(f"{service}_service")
            config = lanying_config.get_lanying_connector(appId)
            if config:
                newConfig = copy.deepcopy(config)
                newConfig['from_user_id'] = fromUserId
                responseText = service_module.handle_chat_message(content, newConfig)
                logging.debug(f"responseText:{responseText}")
                sendMessage(appId, fromUserId, toUserId, responseText)
                msgSentCnt+=1
    except Exception as e:
        logging.error(f"Error:{e}")
        message_404 = lanying_config.get_message_404(appId)
        sendMessage(appId, fromUserId, toUserId, message_404)
        msgSentCnt+=1

def sendMessage(appId, fromUserId, toUserId, content):
    adminToken = lanying_config.get_lanying_admin_token(appId)
    apiEndpoint = lanying_config.get_lanying_api_endpoint(appId)
    if adminToken:
        sendResponse = requests.post(apiEndpoint + '/message/send',
                                    headers={'app_id': appId, 'access-token': adminToken},
                                    json={'type':1, 'from_user_id':toUserId,'targets':[fromUserId],'content_type':0, 'content': content})
        logging.debug(sendResponse)
