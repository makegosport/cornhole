from make_game import makegame as game
import threading
import paho.mqtt.client as mqtt
import configparser
import time
import keyboard

class SimulatedGame(Game):

    def __init__(self):
        super().__init__()

        self.game_running = False

    def start_game(self):
        self.game_running = True
        keyboard.on_press(self.process_key_press)

    def process_key_press(self, keyboard_event: keyboard.KeyboardEvent):

        if keyboard_event.name == 'q':
            print('Quit key pressed')
            self.game_running = False
        elif keyboard_event.name == 'r':
            print('red bag - 10 points scored')
            self.incscore(10)
        elif keyboard_event.name == 'b':
            print('red bag - 20 points scored')
            self.incscore(20)
        elif keyboard_event.name == 'e':
            client.publish('cornhole/endgame', payload=f'score={newgame.score}', qos=0,
                           retain=False)
            self.reset()

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



client = mqtt.Client(str(uuid.uuid4())+'cornhole_game')
client.on_connect = on_connect
client.on_message = on_message

client.connect_async(mqttserver, mqttport, mqttkeepalive)

# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
client.loop_start()
client.subscribe("$SYS/#")
newgame = SimulatedGame()

newgame.start_game()
while newgame.game_running:
    pass

client.loop_stop()
client.disconnect()
