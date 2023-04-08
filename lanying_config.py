import etcd3
import logging
import json
import os

prefix = os.getenv('LANYING_CONNECTOR_APP_CONFIG_PREFIX')
configs = {}
mode = 'env'
etcd = None

def key_changed(watch_response):
    for event in watch_response.events:
        if isinstance(event, etcd3.events.PutEvent):
            configs[event.key.decode("utf-8") ] = parse_value(event.value)
        elif isinstance(event, etcd3.events.DeleteEvent):
            configs.pop(event.key.decode("utf-8"))

def init():
    etcdServer = os.getenv('LANYING_CONNECTOR_ETCD_SERVER')
    etcdPort = os.getenv('LANYING_CONNECTOR_ETCD_PORT')
    if etcdServer != None and etcdPort != None:
        global mode
        global etcd
        mode = 'etcd'
        etcd = etcd3.client(host = etcdServer, port=etcdPort)
        for (value, meta) in etcd.get_prefix(prefix):
            configs[meta.key.decode("utf-8") ] = parse_value(value)
        etcd.add_watch_prefix_callback(prefix, key_changed)

def parse_value(value):
    try:
        return json.loads(value)
    except Exception as e:
        return None

def get_config(appId, key, default):
    return configs.get(prefix + appId + '.'+key, default)

def save_config(appId, key, value):
    global etcd
    if etcd:
        etcd.put(prefix + appId + '.'+key, value)

def get_config_field(appId, key, field, default):
    value = configs.get(prefix + appId + '.'+key)
    if value:
        return value.get(field, default)
    return default

def get_all_config():
    return configs

def get_lanying_user_id(appId):
    if mode == 'etcd':
        return get_config_field(appId, 'lanying_connector', 'lanying_user_id', None)
    return os.getenv('LANYING_USER_ID')

def get_lanying_connector_service(appId):
    if mode == 'etcd':
        return get_config_field(appId, 'lanying_connector', 'lanying_connector_service', None)
    return os.getenv('LANYING_CONNECTOR_SERVICE')

def get_message_404(appId):
    if mode == 'etcd':
        return get_config_field(appId, 'lanying_connector', 'lanying_connector_message_404', "抱歉，因为某些无法说明的原因，我暂时无法回答你的问题。")
    return os.getenv('LANYING_CONNECTOR_MESSAGE_404')

def get_message_antispam(appId):
    if mode == 'etcd':
        return get_config_field(appId, 'lanying_connector', 'lanying_connector_message_antispam', "对不起，因为系统设定的原因，这个问题我无法回答，请您谅解。")
    return os.getenv('LANYING_CONNECTOR_MESSAGE_ANTISPAM')

def get_lanying_admin_token(appId):
    if mode == 'etcd':
        return get_config_field(appId, 'lanying_connector', 'lanying_admin_token', None)
    return os.getenv('LANYING_ADMIN_TOKEN')

def get_lanying_callback_signature(appId):
    if mode == 'etcd':
         return get_config_field(appId, 'lanying_connector', 'lanying_callback_signature', None)
    return os.getenv('LANYING_CALLBACK_SIGNATURE')

def get_lanying_connector_expire_time(appId):
    if mode == 'etcd':
        return get_config(appId, 'lanying_connector.expire_time', None)
    return -1

def get_lanying_connector(appId):
    if mode == 'etcd':
        return get_config(appId, 'lanying_connector', None)
    service = get_lanying_connector_service(appId)
    if service == 'openai':
        with open(f"configs/{service}.json", "r") as f:
            config = json.load(f)
            openaiAPIKey = os.getenv('OPENAI_API_KEY')
            if openaiAPIKey:
                config['openai_api_key'] = openaiAPIKey
            return config

def get_lanying_connector_default_openai_api_key():
    return os.getenv('OPENAI_API_KEY')

def get_lanying_api_endpoint(appId):
    return os.getenv('LANYING_API_ENDPOINT', 'https://s-1-3-api.maximtop.cn')