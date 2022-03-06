import random
import time

import paho.mqtt.client as mqtt

class MakeGame:
    def __init__(self, configdata, mqtt_client: mqtt.Client):

        self.colours = configdata['colours']
        self.nHoles = int(configdata['nHoles'])
        self.difficulty = int(configdata['difficulty'])
        self.gametime = int(configdata['gametime'])
        self.__mqtt = mqtt_client
        self.holes = [_GameHole(x, mqtt_client, x*10) for x in range(self.nHoles)]

    @property
    def score(self):
        """
        The total score by adding up all the holes
        """
        return sum(hole.score for hole in self.holes)

    def _reset_holes(self):
        """
        Turn off all the holes
        """
        for hole in self.holes:  # Turn all holes off at start of game
            hole.off()
            hole.reset()

    def reset(self):
        score_before_reset = self.score
        self._reset_holes()
        return(score_before_reset)
        
    def printscore(self):
        print('The current score is: ' + str(self.score))

    def startgame(self):
        start_time = time.time()
        finish_time = time.time() + self.gametime
        self._reset_holes()  # this also zeros out the scores

        # main game loop
        while time.time() < finish_time:
            rel_time = time.time() - start_time
            for hole in self.holes:
                if hole.offtime <= rel_time:
                    if random.choice([True, False]): # Will hole be on or off?
                        random_colour = random.choice(self.colours)
                        hole.set(random_colour)
                    else:
                        hole.off()
                    hole.offtime = random.choice(range(3,5)) # Sleep time for the hole
                self.__mqtt.publish('game/current_score', f'{self.score:d}')
            time.sleep(0.1)

        self.__mqtt.publish('game/end_score', self.score)

class _GameHole:
    def __init__(self, id, mqtt_client: mqtt.Client, points: int):
        self.id = id

        self.offtime = 0
        self.abs_offtime = 0
        self.__mqtt = mqtt_client
        self.points = points
        self.score = 0
        self.status = False

    def set(self, colour: str):
        """
        Turn the hole on with a specified colour
        :param colour:
        :return:
        """
        self.__mqtt.publish(f'holes/{self.id:d}/colour', colour)
        self.status = True
        self.__mqtt.publish(f'holes/{self.id:d}/state', 'on')

    def off(self):
        self.__mqtt.publish(f'holes/{self.id:d}/state', 'off')

    def hit(self):
        """
        An item has landed in the hole, however it only gets the score incremented if the hole was
        active, if the hole is hit when the hole is off it subtracts points
        """
        if self.status is True:
            self.score += self.points
            self.__mqtt.publish(f'holes/{self.id:d}/hit', 'valid')
        else:
            self.score -= self.points
            self.__mqtt.publish(f'holes/{self.id:d}/hit', 'invalid')

    def reset(self):
        self.score=0

