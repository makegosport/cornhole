"""
This module implements a stand alone application which does the following:

#. Subscribes to an Cornhole MQTT Broker
#. When a update MQTT message occurs for example a game is completed it will tweet out a result
"""
import uuid
from datetime import datetime
import os
import argparse
import logging.config
import re
import json
from dataclasses import dataclass
from typing import Optional

import paho.mqtt.client as mqtt

from cheer_lights_twitter_api import CheerLightTwitterAPI, CheerLightColours
from tweepy_wrapper import TwitterAPIVersion

file_path = os.path.dirname(__file__)

@dataclass
class HoleState:
    state: bool
    colour: CheerLightColours

class CornHoleTweeter(CheerLightTwitterAPI):
    """
    Main Class

    Args:
        user_template_dir (str): Path to a directory where user-defined jinja template overrides are stored.
        user_template_context (dict): Additional context variables to load into the template namespace.

    """
    _DEFAULT_MQTT_SERVER = 'localhost'
    _DEFAULT_MQTT_SERVER_PORT = 1883

    def __init__(self, **kwargs):

        self.__logger = logging.getLogger('CornHoleTweeter')

        # initialise the mqtt part of the class
        self.__my_uuid = uuid.uuid4()
        self.__mqtt_client = mqtt.Client(str(self.__my_uuid)+'_cornhole_tweeter')

        mqtt_server = kwargs.pop('mqtt_server', self._DEFAULT_MQTT_SERVER)
        if not isinstance(mqtt_server, str):
            raise TypeError(f'mqtt_server should be of type bool, got {type(mqtt_server)}')
        self.__mqtt_host = mqtt_server

        mqtt_port = kwargs.pop('mqtt_port', self._DEFAULT_MQTT_SERVER_PORT)
        if not isinstance(mqtt_port, int):
            raise TypeError(f'mqtt_server should be of type bool, got {type(mqtt_server)}')
        self.__mqtt_port = mqtt_port

        # initialise the tweeting part of the class
        if 'user_template_dir' not in kwargs:
            kwargs['user_template_dir'] = os.path.join(file_path, 'cornhole_templates')
        super().__init__(**kwargs)

    def mqtt_connect(self):
        self.__mqtt_client.connect(host=self.__mqtt_host,
                                   port=self.__mqtt_port)
        self.__mqtt_client.on_message = self.on_message  # attach function to callback
        self.__mqtt_client.on_connect = self.on_connect

        self.__mqtt_client.loop_start()

    def mqtt_disconnect(self):
        self.__mqtt_client.loop_stop(force=True)

    def connect(self):
        self.mqtt_connect()
        super().connect()

    def disconnect(self):
        self.mqtt_disconnect()
        super().disconnect()

    def on_connect(self, client, userdata, flags, rc):

        if rc == 0:
            self.__logger.info("Successfully connected to broker")

        self.__mqtt_client.subscribe('ui/#')
        self.__mqtt_client.subscribe('game/status')


    def on_message(self, client, userdata, message):

        topic_match = re.match(r'game/status', message.topic)
        if topic_match is not None:

            message_payload = message.payload.decode('utf-8')
            payload_content = json.loads(message_payload)

            if payload_content['status'] == 'end':
                if self.is_follower(screen_name=payload_content['username']):

                    score = payload_content['score']

                    if score < 10:
                        colour = CheerLightColours.RED
                    elif score < 50:
                        colour = CheerLightColours.BLUE
                    else:
                        colour = CheerLightColours.GREEN


                    self.endgame_tweet(score=payload_content['score'],
                                       username=payload_content['username'],
                                       colour=colour)

            return None

        topic_match = re.match(r'ui/', message.topic)
        if topic_match is not None:
            message_payload = message.payload.decode('utf-8')

            self.__logger.info(f'mqtt username update {message_payload}')
            user_name = message_payload

            follower = self.is_follower(user_name)
            if follower:
                self.__mqtt_client.publish(f'twitter/{user_name}', 'True')
            else:
                self.__mqtt_client.publish(f'twitter/{user_name}', 'False')

            return None

        self.__logger.error(f'received an unexpected mqtt {message.topic=}')

    def endgame_tweet(self, score, username, colour) -> Optional[int]:
        """
        Send a tweet based on a Jinja template

        Args:
            score (int) : user score for the game
        Returns:
            The tweet sent out
        """
        # if the payload is None then build off the template
        tweet_content = self.colour_template_tweet(jinja_context={'current_score':score,
                                                                  'user_name': username},
                                                   colour=colour)

        return tweet_content

# set up the command line arguments for calling the application
parser = argparse.ArgumentParser(description='Python Code to generate a Cornhole Tweet based on MQTT message')
parser.add_argument('--mqtt_server', '-a', dest='mqtt_server', type=str, default='192.168.1.120',
                    help='address for the MQTT server')
parser.add_argument('--mqtt_port', '-p', dest='mqtt_port', type=int, default=1883,
                    help='port for the MQTT server')
parser.add_argument('--verbose', '-v', dest='verbose', action='store_true',
                    help='All the logging information will be shown in the console')
parser.add_argument('--suppress_tweeting', '-s', dest='suppress_tweeting', action='store_true',
                    help='Makes the connection to twitter but will suppress any update status, '
                         'this is useful for testing')
parser.add_argument('--suppress_connection', '-c', dest='suppress_connection', action='store_true',
                    help='Does not connect to the twitter API, this is useful for testing')
parser.add_argument('--generate_access', '-g', dest='generate_access', action='store_true',
                    help='generate the user access token via a web confirmation')
#parser.add_argument('--destroy_tweet', '-d', dest='destroy_tweet', action='store_true',
#                    help='destroy (delete) the tweet created which is useful in testing')
parser.add_argument('--twitter_api_version', type=str, default='V1',
                    choices=[choice.name for choice in TwitterAPIVersion])

if __name__ == "__main__":

    # parse the command line args
    command_args = parser.parse_args()

    # set up the logging configuration
    if command_args.verbose:
        LOGGING_CONFIG = {
            'version': 1,
            'disable_existing_loggers': True,
            'formatters': {
                'standard': {
                    'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
                },
            },
            'handlers': {
                'default': {
                    'level': 'INFO',
                    'formatter': 'standard',
                    'class': 'logging.StreamHandler',
                    'stream': 'ext://sys.stdout',  # Default is stderr
                },
            },
            'loggers': {
                '': {  # root logger
                    'handlers': ['default'],
                    'level': 'DEBUG',
                    'propagate': False
                },
                '__main__': {  # if __name__ == '__main__'
                    'handlers': ['default'],
                    'level': 'DEBUG',
                    'propagate': False
                },
            }
        }
        logging.config.dictConfig(LOGGING_CONFIG)

    corn_hole_tweeter = CornHoleTweeter(mqtt_port=command_args.mqtt_port,
                                        mqtt_server=command_args.mqtt_server,
                                        key_path=file_path,
                                        suppress_tweeting=command_args.suppress_tweeting,
                                        suppress_connection=command_args.suppress_connection,
                                        generate_access=command_args.generate_access,
                                        twitter_api_version=TwitterAPIVersion[command_args.twitter_api_version])
    corn_hole_tweeter.connect()

    while True:
        pass