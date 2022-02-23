from make_game import makegame as game
import threading
import paho.mqtt.client as mqtt
import configparser
import time
import keyboard

#Read the config file
config = configparser.ConfigParser()
config.read('config.txt')


#Initialise the MQTT client

#Read the mqtt section of the config file
mqttconfig = config['mqtt-broker']
mqttserver = mqttconfig.get('Broker', '127.0.0.1')
mqttport = int(mqttconfig.get('Port', 1883))
mqttkeepalive = int(mqttconfig.get('KeepAlive', 60))


# Callback Functions - called on mqtt connection events
# callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("$SYS/broker/uptime")


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))



client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect_async(mqttserver, mqttport, mqttkeepalive)

# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
client.loop_start()
client.subscribe("$SYS/#")
newgame = game

while True:
    if keyboard.is_pressed('q'):
        print('Quit key pressed')
        break
    if keyboard.is_pressed('i'):
        game.incscore(1)
    if keyboard.is_pressed('r'):
        game.reset()
    if keyboard.is_pressed('p'):
        game.printscore()
client.loop_stop()
