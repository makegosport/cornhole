"""
This module provides the core functionality of the game, including:

* The game state, e.g. running, stopped
* controlling the choice of hole colour
* keeping track of the score
"""
import random
import time
import json
import asyncio


class MakeGame:
    """
    Main Game Class

    Args:
        configdata: data from the configuration file
        mqtt: mqtt client instance

    """
    mqtt_attributes = ["status", "score", "colours", "nHoles", "difficulty", "gametime", "score", "start_time", "finish_time", "rel_time"]
    
    def __init__(self, configdata, mqtt):
        self.score = 0
        self.configdata = configdata
        self.status = "off"
        self.mqtt = mqtt
        self.colours = configdata['colours']
        self.nHoles = int(configdata['nHoles'])
        self.difficulty = int(configdata['difficulty'])
        self.gametime = int(configdata['gametime'])
        self.mqtt = mqtt
        self.holes = [gamehole(x, False, self.mqtt, configdata, self.colours) for x in range(self.nHoles)]
        self.start_time = None
        self.finish_time = None
        self.rel_time = None
        self.hole_lt = 1
        self.hole_ut = 5
        self.shutdown_request = False
        self.command = 'standby'
        self.publish()
        
    def main(self):
        while not self.shutdown_request:
            if self.command == 'standby':
                self.standby()
            elif self.command == 'run':
                self.startgame()
        return 'Game exited succesfully'
    
    def reset(self):
        #self.score = 0
        #self.holes = [gamehole(x, False, self.mqtt) for x in range(self.nHoles)]
        self.__init__(self.configdata, self.mqtt)
        self.status = "reset"
        self.publish()
        self.standby()
        
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
        asyncio.run(self.holeroutine())
        for hole in self.holes:
            hole.off()
        self.state = 'end'
        self.command = 'standby'
        self.reset()
        return 'game end'
    
    async def holeroutine(self):
        holetasks = [hole.set() for hole in self.holes]
        asynctasks = asyncio.gather(*holetasks)
        await asyncio.sleep(self.gametime)
        asynctasks.cancel()
        
        #await self.holes[0].set()
    def publish(self):
        self.mqtt.publish('game/status', json.dumps({k:self.__dict__[k] for k in self.mqtt_attributes}))
    
    def standby(self):
        self.state = 'standby'
        self.publish()
        time.sleep(1)
        return self.state
    
    def quit(self):
        self.state = 'off'
        self.publish()
        return self.state
    
        
              
class gamehole:
    """
    Hole
    """
    mqtt_attributes = ["status", "offtime", "id", "colour", ]
    
    def __init__(self, id, status, mqtt, configdata, colour_list):
        self.id = id
        self.status = status
        self.offtime = 0
        self.abs_offtime = 0
        self.mqtt = mqtt
        self.colour = "red"
        #self.publish()
        self.holeconfig = configdata['holeconfig']
        self.onRange = (self.holeconfig['min_on_time'], self.holeconfig['max_on_time'])
        self.offRange = (self.holeconfig['min_off_time'], self.holeconfig['max_off_time'])
        self.probOn = self.holeconfig['prob_on']
        self.colour_list = colour_list
        
    
    async def main(self):
        await self.set()
        
        
    async def set(self):
        if random.choices([True,False], [self.probOn, 1-self.probOn]): 
            self.status = True
            self.colour = random.choice(self.colour_list)
            await self.asyncpublish()
            sleepTime = random.uniform(*self.onRange)
        else:
            self.status = False
            await self.asyncpublish()
            sleepTime = random.uniform(*self.offRange)
        await asyncio.sleep(sleepTime)
            
        
    def off(self):
        self.status = False
        self.publish()
        
    def on(self):
        self.status = True
        self.publish()
    
    def publish(self):
        self.mqtt.publish('holes/' + str(self.id), json.dumps({k:self.__dict__[k] for k in self.mqtt_attributes}))
        
    async def asyncpublish(self):
        self.mqtt.publish('holes/' + str(self.id), json.dumps({k:self.__dict__[k] for k in self.mqtt_attributes}))
        
