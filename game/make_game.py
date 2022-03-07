import random 
import time
import json

class MakeGame:
    mqtt_attributes = ["status", "score", "colours", "nHoles", "difficulty", "gametime", "score", "start_time", "finish_time", "rel_time"]
    
    def __init__(self, configdata, mqtt):
        self.score = 0
        self.status = "off"
        self.mqtt = mqtt
        self.colours = configdata['colours']
        self.nHoles = int(configdata['nHoles'])
        self.difficulty = int(configdata['difficulty'])
        self.gametime = int(configdata['gametime'])
        self.mqtt = mqtt
        self.holes = [gamehole(x, False, self.mqtt) for x in range(self.nHoles)]
        self.start_time = None
        self.finish_time = None
        self.rel_time = None
        self.hole_lt = 1
        self.hole_ut = 5
        
        self.publish()
        
    
    def reset(self):
        self.score = 0
        self.holes = [gamehole(x, False, self.mqtt) for x in range(self.nHoles)]
        self.status = "reset"
        self.publish()
        
    def printscore(self):
        print('The current score is: ' + str(self.score))
        
    def incscore(self, points):
        self.score += points
        
    def startgame(self):
        self.start_time = time.time()
        print(self.start_time)
        self.finish_time = time.time() + self.gametime
        print(self.finish_time)
        self.status = "Init"
        self.publish()
        for hole in self.holes: #Turn all holes off at start of game
            hole.off()
        self.status = "Playing"
        self.publish()
        while time.time() < self.finish_time: #Main game loop
            #print(time.time())
            self.rel_time = time.time() - self.start_time
            for hole in self.holes:
                if hole.offtime <= self.rel_time:
                    if random.choice([True, False]): # Will hole be on or off?
                        hole.set(random.choice(self.colours))
                        print(str(hole.id) + " set to " + hole.colour)
                    else:
                        hole.off()
                        print(str(hole.id) + " set to off")
                    hole.offtime = random.choice(range(1,2)) + self.rel_time # Sleep time for the hole
                    #print(hole.offtime)
        for hole in self.holes:
            hole.off()
        self.status = "end"
        self.publish()
        self.reset()
        
    def publish(self):
        self.mqtt.publish('game/status', json.dumps({k:self.__dict__[k] for k in self.mqtt_attributes}))
              
class gamehole:
    
    mqtt_attributes = ["status", "offtime", "id", "colour", ]
    
    def __init__(self, id, status, mqtt):
        self.id = id
        self.status = status
        self.offtime = 0
        self.abs_offtime = 0
        self.mqtt = mqtt
        self.colour = "red"
        self.publish()
        
    def set(self, colour):
        self.colour = colour
        self.status = True
        self.publish()
        
    def off(self):
        self.status = False
        self.publish()
        
    def on(self):
        self.status = True
        self.publish()   
    
    def publish(self):
        self.mqtt.publish('holes/' + str(self.id), json.dumps({k:self.__dict__[k] for k in self.mqtt_attributes}))