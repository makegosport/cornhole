from make_game import MakeGame as Game
import paho.mqtt.client as mqtt
import configparser
import time
import keyboard
import yaml
import asyncio

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
    client.subscribe("game/switches/#")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))



client = mqtt.Client(str(uuid.uuid4())+'cornhole_game')
client.on_connect = on_connect
client.on_message = on_message

client.connect_async(mqttbroker['broker'], mqttbroker['port'], mqttbroker['KeepAlive'])

#Threaded MQTT handler
client.loop_start()
client.subscribe("$SYS/#")

#Init a game
newgame = Game(gamesettings, client)

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
keyboard.unhook_all()

