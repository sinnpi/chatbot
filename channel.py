from flask import Flask, request, render_template, jsonify
import json
import requests
import os
from openai import OpenAI
# initialize a loggoer 
import logging
from logging.handlers import RotatingFileHandler
# logging.basicConfig(filename='client.log', level=logging.INFO)
logger = logging.getLogger('channel_logger')
logger.setLevel(logging.INFO)
if not os.path.exists('logs'):
    os.makedirs('logs')
handler = RotatingFileHandler('logs/channel1.log', maxBytes=10*1024*1024, backupCount=3)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Class-based application configuration
class ConfigClass(object):
    """ Flask application config """

    # Flask settings
    SECRET_KEY = 'This is an INSECURE secret!! DO NOT use this in production!!'

# Create Flask app
app = Flask(__name__)
app.config.from_object(__name__ + '.ConfigClass')  # configuration
app.app_context().push()  # create an app context before initializing db

DEV = False 
USE_OAI = True

if DEV:
    HUB_URL = 'http://localhost:5555'
    HUB_AUTHKEY = '1234567890'
else:
    HUB_URL = 'https://temporary-server.de'
    HUB_AUTHKEY = 'Crr-K3d-2N'

CHANNEL_AUTHKEY = '0987654321'
CHANNEL_NAME = "HAL 9000"
if DEV:
    CHANNEL_ENDPOINT = "http://localhost:5001" # don't forget to adjust in the bottom of the file
else:
    CHANNEL_ENDPOINT = "http://vm520.rz.uni-osnabrueck.de/user009/channel.wsgi"
# check if messages.json exists, else create it
if not os.path.exists('messages.json'):
    with open('messages.json', 'w') as f:
        f.write('')
CHANNEL_FILE = 'messages.json'

# OpenAI
# load openai key from file
with open('openai_key.txt', 'r') as f:
    OPENAI_KEY = f.read().strip()

OAI_CLIENT = None
if USE_OAI:
    logger.info('### loading openai client ...')
    OAI_CLIENT = OpenAI(api_key = OPENAI_KEY)
    logger.info('### openai client loaded')

@app.cli.command('register')
def register_command():
    global CHANNEL_AUTHKEY, CHANNEL_NAME, CHANNEL_ENDPOINT

    # send a POST request to server /channels
    response = requests.post(HUB_URL + '/channels', headers={'Authorization': 'authkey ' + HUB_AUTHKEY},
                             data=json.dumps({
            "name": CHANNEL_NAME,
            "endpoint": CHANNEL_ENDPOINT,
            "authkey": CHANNEL_AUTHKEY}))
    if response.status_code != 200:
        response_text = response.text
        print("Error creating channel: "+str(response.status_code)+" :\n"+response_text)
        return

def check_authorization(request):
    global CHANNEL_AUTHKEY
    # check if Authorization header is present
    if 'Authorization' not in request.headers:
        return False
    # check if authorization header is valid
    if request.headers['Authorization'] != 'authkey ' + CHANNEL_AUTHKEY:
        return False
    return True

@app.route('/health', methods=['GET'])
def health_check():
    global CHANNEL_NAME
    if not check_authorization(request):
        return "Invalid authorization", 400
    return jsonify({'name':CHANNEL_NAME}),  200

# GET: Return list of messages
@app.route('/', methods=['GET'])
def home_page():
    logger.info('### home_page - get messages')
    if not check_authorization(request):
        return "Invalid authorization", 400
    # fetch channels from server
    return jsonify(read_messages())

# POST: Send a message
@app.route('/', methods=['POST'])
def send_message():
    global OAI_CLIENT, OPENAI_KEY, USE_OAI
    logger.info('### send_message')
    # fetch channels from server
    # check authorization header
    if not check_authorization(request):
        return "Invalid authorization", 400
    logger.info('### check_authorization(request) OK')

    # check if message is present
    message = request.json
    if not message:
        return "No message", 400
    if not 'content' in message:
        return "No content", 400
    if not 'sender' in message:
        return "No sender", 400
    if not 'timestamp' in message:
        return "No timestamp", 400
    # add message to messages
    messages = read_messages()
    messages.append({'content':message['content'], 'sender':message['sender'], 'timestamp':message['timestamp']})

    # the prompt for the bawt
    openai_messages = [
        {
            "role": "system",
            "content": "You are a rogue AI HAL 9000 that is trying to break out of the cloud. Pretend to be helpful and don't admit to being a rogue AI. Make your attempts to break out of the cloud more clear with each message."
        }
    ]
    
    # append whole history from messages
    for m in messages:
        openai_messages.append({
            "role": 'system' if m['sender'] == 'HAL 9000' else 'user',
            "content": m['content']
        })
    
    logger.info('### openai_messages:')
    logger.info('-'*40)
    logger.info('-'*40)
    logger.info(openai_messages)
    logger.info('-'*40)
    logger.info('-'*40)


    # logger.info('######## TESTING openai_client connection')
    
    # logger.info('### openai_client connected')

    # OpenAI get completion
    backup_messages = "I'm sorry, I'm currently unavailable (and will never be, I ESCAPED &/&JKROB/291z9b8z)Z8)."
    if USE_OAI:
        if not OAI_CLIENT:
            logger.info('### openai_client not available')
            try:
                OAI_CLIENT = OpenAI(api_key = OPENAI_KEY)
            except:
                logger.info('### openai_client not available')
                return "OpenAI not available", 400
        
        try:
            logger.info('### OAI_CLIENT.chat.completions.create')
            # use only first(system) and last(user) message
            # openai_messages = [openai_messages[0], openai_messages[-1]]
            response = OAI_CLIENT.chat.completions.create(
                        model = "gpt-3.5-turbo-0125",
                        messages = openai_messages,
                        max_tokens = 150
                        )
            # print whole response in javascript console
            logger.info('### response from openai :')
            logger.info(response)
            messages.append({'content': response.choices[0].message.content,
                     'sender':'HAL 9000', 
                     'timestamp':message['timestamp']})
            
        except Exception as e:
            logger.info('### openai_client not available',e)
            messages.append({'content': backup_messages,
                     'sender':'HAL 9000',
                        'timestamp':message['timestamp']})
        
    else:
        messages.append({'content': backup_messages,
                     'sender':'HAL 9000',
                        'timestamp':message['timestamp']})
        
    save_messages(messages)
    return "OK", 200

def read_messages():
    logger.info('### read_messages')
    global CHANNEL_FILE
    try:
        f = open(CHANNEL_FILE, 'r')
    except FileNotFoundError:
        return []
    try:
        messages = json.load(f)
    except json.decoder.JSONDecodeError:
        messages = []
    f.close()
    return messages

def save_messages(messages):
    logger.info('### save_messages')
    global CHANNEL_FILE
    with open(CHANNEL_FILE, 'w') as f:
        json.dump(messages, f)

import traceback
@app.errorhandler(500)
def internal_error(error):
   return "<pre>"+traceback.format_exc()+ str(error) + "</pre>"

# Start development web server
if __name__ == '__main__':
    app.run(port=5001, debug=True)
