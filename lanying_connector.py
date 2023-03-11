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
from redis import StrictRedis, ConnectionPool

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
executor = ThreadPoolExecutor(8)
sys.path.append("services")
lanying_config.init()
app = Flask(__name__)
if os.environ.get("FLASK_DEBUG"):
    app.debug = True

redisServer = os.getenv('LANYING_CONNECTOR_REDIS_SERVER')
redisPool = None
if redisServer:
    redisPool = ConnectionPool.from_url(redisServer)

accessToken = os.getenv('LANYING_CONNECTOR_ACCESS_TOKEN')

@app.route("/", methods=["GET"])
def index():
    service = lanying_config.get_lanying_connector_service('')
    return render_template("index.html", msgReceivedCnt=getMsgReceivedCnt(), msgSentCnt=getMsgSentCnt(), service=service)

@app.route("/messages", methods=["POST"])
def messages():
    addMsgReceivedCnt(1)
    text = request.get_data(as_text=True)
    data = json.loads(text)
    logging.debug(data)
    fromUserId = data['from']['uid']
    toUserId = data['to']['uid']
    type = data['type']
    ctype = data['ctype']
    appId = data['appId']
    callbackSignature = lanying_config.get_lanying_callback_signature(appId)
    if callbackSignature and len(callbackSignature) > 0:
        headSignature = request.headers.get('signature')
        if callbackSignature != headSignature:
            logging.info(f'callback signature not match: appId={appId}')
            resp = app.make_response('callback signature not match')
            return resp
    myUserId = lanying_config.get_lanying_user_id(appId)
    logging.debug(f'lanying_user_id:{myUserId}')
    if myUserId != None and toUserId == myUserId and fromUserId != myUserId and type == 'CHAT' and ctype == 'TEXT':
        executor.submit(queryAndSendMessage, data)
    resp = app.make_response('')
    return resp

@app.route("/config", methods=["POST"])
def saveConfig():
    headerToken = request.headers.get('access-token', "")
    if accessToken and accessToken == headerToken:
        text = request.get_data(as_text=True)
        data = json.loads(text)
        appId = data['app_id']
        value = data['value']
        lanying_config.save_config(appId, 'lanying_connector', value)
        resp = app.make_response('success')
        return resp
    resp = app.make_response('fail')
    return resp

@app.route("/config", methods=["GET"])
def getConfig():
    showConfigAppId = os.getenv('LANYING_CONNECTOR_SHOW_CONFIG_APP_ID')
    if showConfigAppId:
        config = lanying_config.get_lanying_connector(showConfigAppId)
        resp = app.make_response(json.dumps(config['preset']['messages'], ensure_ascii=False))
        return resp
    resp = app.make_response('')
    return resp

def queryAndSendMessage(data):
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
                newConfig['to_user_id'] = toUserId
                responseText = service_module.handle_chat_message(content, newConfig)
                logging.debug(f"responseText:{responseText}")
                sendMessage(appId, fromUserId, toUserId, responseText)
                addMsgSentCnt(1)
    except Exception as e:
        logging.exception(e)
        message_404 = lanying_config.get_message_404(appId)
        sendMessage(appId, fromUserId, toUserId, message_404)
        addMsgSentCnt(1)

def sendMessage(appId, fromUserId, toUserId, content):
    adminToken = lanying_config.get_lanying_admin_token(appId)
    apiEndpoint = lanying_config.get_lanying_api_endpoint(appId)
    message_antispam = lanying_config.get_message_antispam(appId)
    if adminToken:
        sendResponse = requests.post(apiEndpoint + '/message/send',
                                    headers={'app_id': appId, 'access-token': adminToken},
                                    json={'type':1, 'from_user_id':toUserId,'targets':[fromUserId],'content_type':0, 'content': content, 'config': json.dumps({'antispam_prompt':message_antispam}, ensure_ascii=False)})
        logging.debug(sendResponse)

def getRedisConnection():
    conn = None
    if redisPool:
        conn = StrictRedis(connection_pool=redisPool)
    if not conn:
        logging.warning(f"getRedisConnection: fail to get connection")
    return conn

def addMsgSentCnt(num):
    redis = getRedisConnection()
    if redis:
        redis.incrby(msgSentCntKey(), num)

def addMsgReceivedCnt(num):
    redis = getRedisConnection()
    if redis:
        redis.incrby(msgReceivedCntKey(), num)

def getMsgSentCnt():
    redis = getRedisConnection()
    if redis:
        str = redis.get(msgSentCntKey())
        if str:
            return int(str)
    return 0

def getMsgReceivedCnt():
    redis = getRedisConnection()
    if redis:
        str = redis.get(msgReceivedCntKey())
        if str:
            return int(str)
    return 0

def msgSentCntKey():
    return "lanying:connector:msg:sent:cnt"

def msgReceivedCntKey():
    return "lanying:connector:msg:received:cnt"
