"""
This module manages the the game instance and handles the MQTT connection and inbound messages
"""
import json
import time
import logging.config
import uuid
import asyncio
from os.path import exists
import argparse

import yaml
import paho.mqtt.client as mqtt

from make_game import MakeGame as Game

def readconfigfile(inputfile):
    logging.info("Reading config file: config.yaml")
    with open(inputfile, "r") as configfile:
        try:
            config = yaml.safe_load(configfile)
            mqttbroker = config['mqttbroker']
            gamesettings = config['gamesettings']
            switchsettings = config['switchsettings']
            logconf = config['logs']
        except Exception as e:
            logging.error(e)
    logging.debug(configfile)
    return mqttbroker, gamesettings, switchsettings, logconf


#MQTT client callback Functions

# Callback Functions - called on mqtt connection events
# callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    global newgame
    newgame.shutdown_request = False
    if rc == 0:
        logging.info("Successfully connected to broker")
    print("Connected with result code "+str(rc))
    print("Go to http://127.0.0.1/ui")
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("game/#")
    client.subscribe("switch/#")
    client.subscribe("twitter/#")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    global newgame
    global gamesettings
    msg.payload = str(msg.payload.decode("utf-8"))
    logging.debug(msg.topic+" "+msg.payload)

    if msg.topic == 'game/status':
        return True

    if msg.topic == "game/control":# and not gamethread.is_alive():
        if msg.payload == 'reset':
            newgame.reset()
        elif msg.payload == 'newgame':
            newgame.command = 'run' 
        elif msg.payload == 'reconfig':
            _, gamesettings, _, _ = readconfigfile('config.yaml')
            newgame = Game(gamesettings, client)
        elif msg.payload == 'exit':
            newgame.shutdown_request = True
        else:
            logging.error("Unrecognised Payload:" + str(msg))
        return True

    if msg.topic == "game/user":
        newgame.user_name = msg.payload
        return True

    if msg.topic == f'twitter/{newgame.user_name}':
        if msg.payload == 'True':
            newgame.twitter_follower = True
            logging.info(f'{newgame.user_name} is twitter follower')
        elif msg.payload == 'False':
            newgame.twitter_follower = False
            logging.info(f'{newgame.user_name} is not twitter follower')
        else:
            logging.info(f'{msg.topic} unhandled payload {msg.payload}')
        return True

    if msg.topic == "game/detector":
        detected_colour = msg.payload
        newgame.colour_detected(detected_colour)
        return True

    for switch_id in range(1, gamesettings['nHoles']+1):
        if msg.topic == f'switch/{switch_id}':
            # payload of the message
            payload_dict = json.loads(msg.payload)
            newgame.switch_event(id=switch_id, **payload_dict)
            return True

    logging.warning(f'unhandled MQTT: {msg.topic} {msg.payload}')



if exists('game/config.yaml'):
    conf_file = 'game/config.yaml'
elif exists('config.yaml'):
    conf_file = 'config.yaml'
else:
    logging.error("Cannot find config file")
    quit()
mqttbroker, gamesettings, switchsettings, logconf = readconfigfile(conf_file)

#configure logging
logconf = {
    'version': 1,
    'loggers': {
        'root': logconf
    }
}
logging.config.dictConfig(logconf)

#Parse command line arguments (e.g. to determine if running in Docker stack)
parser = argparse.ArgumentParser(description='Python Code to control the Make Gosport Cornhole game',
                                     epilog='https://github.com/makegosport/cornhole '
                                            'for more details')
parser.add_argument('--docker', dest='inDocker', action='store_true',
                    help='If the running in a docker instance')
# parse the command line args
command_args = parser.parse_args()
if command_args.inDocker is True:
    mqttbroker['broker'] = 'broker'
    logging.info('Docker mode requested')
else:
    logging.info('Running in without docker')

#MQTT Client Configuration
client = mqtt.Client(str(uuid.uuid4())+'cornhole_game')
client.on_connect = on_connect
client.on_message = on_message
logging.debug("Defining connection to broker")
client.connect_async(mqttbroker['broker'], mqttbroker['port'], mqttbroker['KeepAlive'])

# configure the switch
client.publish(f'switch/interval', switchsettings['interval'], retain=True)
client.publish(f'switch/hold_off', switchsettings['hold_off'], retain=True)

#Init a game
newgame = Game(gamesettings, client)

#Threaded MQTT handler
if command_args.inDocker:
    logging.info("Starting connection, waiting for 5 seconds for broker to spawn")
    time.sleep(5)
else:
    logging.info("Starting connection: Ensure that your MQTT broker is running at " + str(mqttbroker['broker']) + ":" + str(mqttbroker['port']))

print('Starting MQTT listener')
print(client)
client.loop_start()
asyncio.run(newgame.main())
client.loop_stop()
print('Game thread complete')