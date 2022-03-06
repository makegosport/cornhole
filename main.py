import uuid

from make_game import MakeGame as Game
import paho.mqtt.client as mqtt

import keyboard
import yaml


class SimulatedGame(Game):
    """
    Class to simulate the game board, rather than throwing bags into holes, the number keys
    are used to simulate a bag landing in the hole
    """
    def __init__(self, configdata, mqtt_client: mqtt.Client):
        super().__init__(configdata, mqtt_client)
        self.__mqtt = mqtt_client

        self._hole_keys = [f'{x+1:d}' for x in range(self.nHoles)]

    def enter_name(self):
        name = input('Please Enter You Name')
        self.__mqtt.publish(f'game/username', name)

    def startgame(self):
        self.enter_name()
        print(f'press keys 1 to {self.nHoles:d}  to simulate hits')
        keyboard.on_press(self.process_key_press)
        super().startgame()

        print(f'game over with a score of {self.score}')


    def process_key_press(self, keyboard_event: keyboard.KeyboardEvent):

        if keyboard_event.name in self._hole_keys:
            hole = int(keyboard_event.name)
            self.holes[hole-1].hit()

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



client = mqtt.Client(str(uuid.uuid4())+'_cornhole_game')
client.on_connect = on_connect
client.on_message = on_message

client.connect_async(mqttbroker['broker'], mqttbroker['port'], mqttbroker['KeepAlive'])

#Threaded MQTT handler
client.loop_start()
client.subscribe("$SYS/#")

#Init a game
simulated_game = SimulatedGame(gamesettings, client)
simulated_game.startgame()  # this blocks whilst the game is running


client.loop_stop()
keyboard.unhook_all()

