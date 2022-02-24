from make_game import MakeGame as Game
import paho.mqtt.client as mqtt
import keyboard
import yaml
import asyncio

#Read the config file
with open("config.yaml", "r") as configfile:
    try:
        config = yaml.safe_load(configfile)
        mqttbroker = config['mqttbroker']
        gamesettings = config['gamesettings']
    except:
        print(exc)

#Initialise the MQTT client

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

# Keyboard event callback
def keyboard_handler(event):
    if event.name == 'r':
        newgame.reset()
    elif event.name == 'i':
        newgame.incscore(1)
    elif event.name == 'p':
        newgame.printscore()
    elif event.name == 'q':
        pass
    else:
        print(event.name + ' key not assigned')
        

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect_async(mqttbroker['broker'], mqttbroker['port'], mqttbroker['KeepAlive'])

#Threaded MQTT handler
client.loop_start()
client.subscribe("$SYS/#")

#Init a game
newgame = Game(gamesettings, client)

#Threaded keyboard event handler
keyboard.on_release(keyboard_handler) 
#keyboard.wait('q')

newgame.startgame()

# Clean up    
client.loop_stop()
keyboard.unhook_all()

