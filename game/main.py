from make_game import MakeGame as Game
import paho.mqtt.client as mqtt
import yaml
import time
#import threading
import logging
import uuid
import asyncio

#Read the config file
def readconfigfile(inputfile):
    logging.info("Reading config file: config.yaml")
    with open(inputfile, "r") as configfile:
        try:
            config = yaml.safe_load(configfile)
            mqttbroker = config['mqttbroker']
            gamesettings = config['gamesettings']
        except Exception as e:
            logging.error(e)
    logging.debug(configfile)
    return mqttbroker, gamesettings
#Initialise the MQTT client

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
#    gamethread = threading.Thread()
    msg.payload = str(msg.payload.decode("utf-8"))
    print(msg.topic+" "+msg.payload) 
    if msg.topic == "game/control":# and not gamethread.is_alive():
        if msg.payload == 'reset':
            newgame.reset()
        elif msg.payload == 'inc_score':
            newgame.incscore(1)
        elif msg.payload == 'print':
            newgame.printscore()
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

mqttbroker, gamesettings = readconfigfile('game/config.yaml')
      
client = mqtt.Client(str(uuid.uuid4())+'cornhole_game')
client.on_connect = on_connect
client.on_message = on_message
logging.debug("Defining connection to broker")
client.connect_async(mqttbroker['broker'], mqttbroker['port'], mqttbroker['KeepAlive'])

#Init a game
newgame = Game(gamesettings, client)

#Threaded MQTT handler
logging.info("Starting connection, waiting for 5 seconds for broker to spawn")
time.sleep(5)
print('Starting MQTT listener')
print(client)
client.loop_start()

newgame.main()
client.loop_stop
print('Game thread complete')







