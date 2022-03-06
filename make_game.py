import random
import time
class MakeGame:
    def __init__(self, configdata, mqtt):
        self.score = 0
        self.colours = configdata['colours']
        self.nHoles = int(configdata['nHoles'])
        self.difficulty = int(configdata['difficulty'])
        self.gametime = int(configdata['gametime'])
        self.mqtt = mqtt
        self.holes = [gamehole(x, 'off', mqtt) for x in range(self.nHoles)]

    def reset(self):
        self.score = 0
        return(self.score)
        
    def printscore(self):
        print('The current score is: ' + str(self.score))
        
    def incscore(self, points):
        self.score += points

    def startgame(self):
        start_time = time.time()
        finish_time = time.time() + self.gametime
        for hole in self.holes: #Turn all holes off at start of game
            hole.off()
        while time.time() < finish_time:
            rel_time = time.time() - start_time
            for hole in self.holes:
                if hole.offtime <= rel_time:
                    if random.choice([True, False]): # Will hole be on or off?
                        hole.set(random.choice(self.colours))
                    else:
                        hole.off()
                    hole.offtime = random.choice(range(3,5)) # Sleep time for the hole
                self.mqtt.publish('game/score', self.score)

class gamehole:
    def __init__(self, id, status, mqtt):
        self.id = id
        self.status = status
        self.offtime = 0
        self.abs_offtime = 0
        self.mqtt = mqtt
    def set(self, colour):
        self.mqtt.publish('holes/' + str(self.id) + '/colour', colour)
        self.mqtt.publish('holes/' + str(self.id) + '/state', 'on')
    def off(self):
        self.mqtt.publish('holes/' + str(self.id) + '/state', 'off')
        self.score += points

