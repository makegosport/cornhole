"""
This module manages the the game instance and handles the MQTT connection and inbound messages
"""
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
            logconf = config['logs']
        except Exception as e:
            logging.error(e)
    logging.debug(configfile)
    return mqttbroker, gamesettings, logconf


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

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    global newgame
    msg.payload = str(msg.payload.decode("utf-8"))
    logging.debug(msg.topic+" "+msg.payload) 
    if msg.topic == "game/control":# and not gamethread.is_alive():
        if msg.payload == 'reset':
            newgame.reset()
        elif msg.payload == 'newgame':
            newgame.command = 'run' 
        elif msg.payload == 'reconfig':
            _, gamesettings = readconfigfile('config.yaml') 
            newgame = Game(gamesettings, client)
        elif msg.payload == 'exit':
            newgame.shutdown_request = True
        else:
            logging.error("Unrecognised Payload:" + str(msg))
        return True
    elif msg.topic == "game/detector":
        detected_colour = msg.payload
        newgame.colour_detected(detected_colour)

if exists('game/config.yaml'):
    conf_file = 'game/config.yaml'
elif exists('config.yaml'):
    conf_file = 'config.yaml'
else:
    logging.error("Cannot find config file")
    quit()
mqttbroker, gamesettings, logconf = readconfigfile(conf_file)

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