from flask import Flask, request, render_template, url_for, redirect
import requests
import urllib.parse
import datetime
import os
# initialize a loggoer 
import logging
from logging.handlers import RotatingFileHandler
# logging.basicConfig(filename='client.log', level=logging.INFO)
logger = logging.getLogger('client_logger')
logger.setLevel(logging.INFO)
# create log directory if it does not exist
if not os.path.exists('logs'):
    os.makedirs('logs')
handler = RotatingFileHandler('logs/client.log', maxBytes=10*1024*1024, backupCount=3)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
app = Flask(__name__)

DEV = False

if DEV:
    HUB_AUTHKEY = '1234567890'
    HUB_URL = 'http://localhost:5555'

else:

    HUB_AUTHKEY = 'Crr-K3d-2N'
    HUB_URL = 'https://temporary-server.de'

CHANNELS = None
LAST_CHANNEL_UPDATE = None


def update_channels():
    logger.info("#### update_channels")
    global CHANNELS, LAST_CHANNEL_UPDATE
    if CHANNELS and LAST_CHANNEL_UPDATE and (datetime.datetime.now() - LAST_CHANNEL_UPDATE).seconds < 60:
        return CHANNELS
    # fetch list of channels from server
    logger.info("#### update_channels: fetching")
    logger.info(HUB_URL + '/channels')
    response = requests.get(HUB_URL + '/channels', headers={'Authorization': 'authkey ' + HUB_AUTHKEY})
    logger.info('#### response:', response)
    logger.info('#### response:', response.text)
    if response.status_code != 200:
        return "Error fetching channels: "+str(response.text), 400
    channels_response = response.json()
    if not 'channels' in channels_response:
        return "No channels in response", 400
    CHANNELS = channels_response['channels']
    LAST_CHANNEL_UPDATE = datetime.datetime.now()
    return CHANNELS


@app.route('/')
def home_page():
    # fetch list of channels from server
    return render_template("home.html", channels=update_channels())


@app.route('/show')
def show_channel():
    # fetch list of messages from channel
    logger.info('#### show_channel')
    show_channel = request.args.get('channel', None)
    logger.info('#### show_channel: '+str(show_channel))

    if not show_channel:
        logger.info('#### show_channel: No channel specified')
        return "No channel specified", 400  
    channel = None
    for c in update_channels():
        if c['endpoint'] == urllib.parse.unquote(show_channel):
            channel = c
            break
    if not channel:
        logger.info('#### show_channel: Channel not found')
        return "Channel not found", 404
    logger.info('#### show_channel: '+str(channel['endpoint']))
    logger.info('#### show_channel: '+str(channel['authkey']))
    response = requests.get(channel['endpoint'], headers={'Authorization': 'authkey ' + channel['authkey']})
    logger.info('#### response: '+str(response))
    # logger.info('#### response.text: '+str(response.text))
    if response.status_code != 200:
        logger.info('#### show_channel: Error fetching messages: '+str(response.text))
        return "Error fetching messages: "+str(response.text), 400
    messages = response.json()
    return render_template("channel.html", channel=channel, messages=messages)


@app.route('/post', methods=['POST'])
def post_message():
    # send message to channel
    logger.info('#### post_message')
    post_channel = request.form['channel']
    if not post_channel:
        return "No channel specified", 400
    channel = None
    for c in update_channels():
        if c['endpoint'] == urllib.parse.unquote(post_channel):
            channel = c
            break
    if not channel:
        return "Channel not found", 404
    message_content = request.form['content']
    message_sender = request.form['sender']
    message_timestamp = datetime.datetime.now().isoformat()
    response = requests.post(channel['endpoint'],
                             headers={'Authorization': 'authkey ' + channel['authkey']},
                             json={'content': message_content, 'sender': message_sender, 'timestamp': message_timestamp})

    logger.info('#### response: '+str(response))
    logger.info('#### response.text: '+str(response.text))

    if response.status_code != 200:
        return "Error posting message: "+str(response.text), 400
    return redirect(url_for('show_channel')+'?channel='+urllib.parse.quote(post_channel))

import traceback
@app.errorhandler(500)
def internal_error(error):
   return "<pre>"+traceback.format_exc()+ str(error) + "</pre>"

# Start development web server
if __name__ == '__main__':
    app.run(port=5005, debug=True)
