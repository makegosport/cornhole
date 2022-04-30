import subprocess
import os
import ipaddress
import uuid
import time
import re
import json
import random
import datetime

import pytest
import paho.mqtt.client as mqtt
import yaml
from faker import Faker
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

@pytest.fixture(scope='module') # this is a module fixture as is constants
def game_configuration():
    """
    Getting the game configuration from the YAML file
    """

    with open(os.path.join('game', 'config.yaml'), "r") as configfile:
        config = yaml.safe_load(configfile)

    yield config

@pytest.fixture
def mqtt_connection(game_configuration):

    client = mqtt.Client(str(uuid.uuid4()) + 'cornhole_test')
    client.connect(host=game_configuration['mqttbroker']['broker'],
                   port=game_configuration['mqttbroker']['port'])

    yield client

@pytest.fixture
def game_fixture():

    game_instance = subprocess.Popen('game_run.bat')
    yield game_instance
    # forcably kill the game (in case it has not exited nicely)
    game_instance.kill()


class UI_Simulator:

    def __init__(self, mqtt_client):
        self.__mqtt_client = mqtt_client
        self._fake = Faker()
        self.generate_user_name()

    def newgame(self):
        self.__mqtt_client.publish('game/control', 'newgame')

    def exitgame(self):
        self.__mqtt_client.publish('game/control', 'exit')

    def generate_user_name(self):
        self.user_name = self._fake.user_name()

    def send_user_name(self):
        self.__mqtt_client.publish('ui/', self.user_name)

class MonitoringFixture:

    def __init__(self, mqtt_client: mqtt.Client):
        self._mqtt_client = mqtt_client
        self._time_zero = time.time()

    def reset_time_zero(self, time_zero):
        self._time_zero = time_zero


def test_config(game_configuration):
    """
    check the configuration can be opened and has some sensible things in it
    """
    assert 'mqttbroker' in game_configuration
    assert 'broker' in game_configuration['mqttbroker']
    assert ipaddress.ip_address(game_configuration['mqttbroker']['broker'])


    assert 'gamesettings' in game_configuration

    assert 'switchsettings' in game_configuration

def test_game(mqtt_connection, game_configuration, game_fixture):

    ui_simulator = UI_Simulator(mqtt_client=mqtt_connection)

    # set up to monitor the holes light commands
    class LightMonitor(MonitoringFixture):

        def __init__(self, mqtt_client: mqtt.Client, number_holes:int):
            super().__init__(mqtt_client=mqtt_client)

            # set up data structures
            self.hole_queue = []
            self.number_holes = number_holes
            for _ in range(self.number_holes):
                self.hole_queue.append([])
            self.current_hole_state = ['off' for _ in range(self.number_holes)]

            # set up mqtt callbacks and subscriptions
            self._mqtt_client.message_callback_add("holes/#", self.on_hole_message)
            self._mqtt_client.subscribe('holes/#')

        def on_hole_message(self, client, userdata, msg):
            pay_load = msg.payload.decode("utf-8")
            topic = msg.topic
            topic_match = re.match(r'holes/(?P<hole_number>\d+)', topic)
            if topic_match is None:
                raise RuntimeError(f'unexpected topic:{topic}')

            hole_number = int(topic_match['hole_number'])
            if 1 <= hole_number <= self.number_holes + 1:
                payload_dict = json.loads(pay_load)
                payload_dict['time_stamp'] = time.time() - self._time_zero
                self.hole_queue[hole_number-1].append(payload_dict)

                status = payload_dict['status']
                if status == False:
                    self.current_hole_state[hole_number-1] = 'off'
                elif status == True:
                    self.current_hole_state[hole_number - 1] = payload_dict['colour']
                else:
                    raise RuntimeError(f'unexpected hole status:{status}')

    light_monitor = LightMonitor(mqtt_client=mqtt_connection,
                                 number_holes=game_configuration['gamesettings']['nHoles'])

    # set up to monitor the start/end game
    class GameStatusMonitor(MonitoringFixture):

        def __init__(self, mqtt_client: mqtt.Client):
            super().__init__(mqtt_client=mqtt_client)

            # set up data structures
            self.status_events = []

            # set up mqtt callbacks and subscriptions
            self._mqtt_client.message_callback_add("game/status", self.on_status_message)
            self._mqtt_client.subscribe('game/status')

        def on_status_message(self, client, userdata, msg):
            pay_load = msg.payload.decode("utf-8")
            payload_dict = json.loads(pay_load)
            payload_dict['time_stamp'] = time.time() - self._time_zero
            self.status_events.append(payload_dict)

    game_status_monitor = GameStatusMonitor(mqtt_client=mqtt_connection)

    mqtt_connection.loop_start()
    ui_simulator.generate_user_name()
    ui_simulator.send_user_name()
    time_zero = time.time()
    game_status_monitor.reset_time_zero(time_zero)
    light_monitor.reset_time_zero(time_zero)
    ui_simulator.newgame()
    # don't throw a bag in the final 1 sec
    expected_end_time = time.time() + game_configuration['gamesettings']['gametime'] - 1
    time.sleep(2) # don't thow a bag in the first 2 sec

    hole_strike_times = []
    hole_strike_id = []
    score_times = [0]
    score = [0]

    while(time.time() < expected_end_time):

        # choose a randon hole
        hole_number = random.randint(1, game_configuration['gamesettings']['nHoles'])
        hole_strike_times.append(time.time() - time_zero)
        hole_strike_id.append(hole_number)
        current_hole_colour = light_monitor.current_hole_state[hole_number-1]
        # score is based on the hole and is multipled by 3 if the hole was lit at the strike time
        strike_score = game_configuration['gamesettings']['hole_scores'][hole_number-1]
        if current_hole_colour != 'off':
            strike_score *= game_configuration['gamesettings']['bonusMult']
        score_times.append(time.time() - time_zero)
        score.append(score[-1]+strike_score)

        mqtt_connection.publish(f'switch/{hole_number:d}',
                                json.dumps({'colour': light_monitor.current_hole_state[hole_number-1]}))


        time.sleep(2)

    # final score
    score_times.append(time.time() - time_zero)
    score.append(score[-1])

    time.sleep(10)  # wait for a period to make sure the game has ended

    # stop all MQTT messages
    mqtt_connection.loop_stop()

    ui_simulator.exitgame()
    print(f'{game_fixture.returncode=}')

    # plat out the game
    fig, ax = plt.subplots(nrows=2, ncols=1, sharex=True, figsize=(16, 10), dpi=100)
    for hole_id in range(game_configuration['gamesettings']['nHoles']):
        # check the final hole light event is switching off the lights at the
        # end of the game
        assert light_monitor.hole_queue[0][-1]['status'] == False
        for hole_event_index in range(len(light_monitor.hole_queue[hole_id]) - 1):
            if light_monitor.hole_queue[hole_id][hole_event_index]['status'] == False:
                continue

            start_time = light_monitor.hole_queue[hole_id][hole_event_index]['time_stamp']
            end_time = light_monitor.hole_queue[hole_id][hole_event_index+1]['time_stamp']
            width = end_time - start_time
            colour = light_monitor.hole_queue[hole_id][hole_event_index]['colour']

            ax[0].add_patch(Rectangle(xy=(start_time, hole_id+0.6), width=width,
                                      height=0.8, facecolor=colour, edgecolor='black', fill=True))

    ax[0].plot(hole_strike_times, hole_strike_id, marker='x', linestyle='none', markersize=20,
               markerfacecolor='black')

    ax[0].set_ylim(0, game_configuration['gamesettings']['nHoles']+1)
    ax[0].set_yticks(range(1, game_configuration['gamesettings']['nHoles']+1))
    ax[0].set_xlim(0, 1.1 * game_configuration['gamesettings']['gametime'])
    ax[0].set_ylabel('Hole')
    ax[0].set_title('Hole Colour State')

    game_score_times = []
    game_score=[]
    final_game_score = None
    for status_event in game_status_monitor.status_events:
        game_score_times.append(status_event['time_stamp'])
        game_score.append(status_event['score'])
        if status_event['status'] == 'end':
            final_game_score = status_event['score']
    ax[1].step(score_times, score,'--', label='score from test bench', where='post')
    ax[1].step(game_score_times, game_score, label='score game/status', where='post')
    ax[1].set_xlabel('Time [s]')
    ax[1].set_ylabel('Score')
    ax[1].set_title('Score Monitor')
    fig.suptitle(f'Simulation for {ui_simulator.user_name}')
    fig.savefig('sim_run_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S') + '.png')

    assert final_game_score is not None
    assert final_game_score == score[-1]








