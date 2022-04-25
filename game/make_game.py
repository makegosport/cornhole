"""
This module provides the core functionality of the game, including:

* The game state, e.g. running, stopped
* controlling the choice of hole colour
* keeping track of the score
"""
import random
from re import S
import time
import json
import asyncio
import logging

class MakeGame:
    """
    Main Game Class

    Args:
        configdata: data from the configuration file
        mqtt: mqtt client instance

    """
    mqtt_attributes = ["status", "score", "colours", "nHoles", "difficulty", "gametime", "score",
                       "start_time", "finish_time", "rel_time"]
    
    def __init__(self, configdata, mqtt):
        self.score = 0
        self.configdata = configdata

        self.shutdown_request = False
        self.command = 'standby'
        self.status = "off"

        self.mqtt = mqtt

        self.holes = [_GameHole(x, False, self.mqtt, configdata, self.colours) for x in range(1, self.nHoles+1)]
        self.start_time = None
        self.finish_time = None
        self.rel_time = None
        self.hole_lt = 1
        self.hole_ut = 5

        self.publish()
        
    async def main(self):
        while not self.shutdown_request:
            if self.command == 'standby':
                await self.standby()
            elif self.command == 'run':
                await self.startgame()
        return 'Game exited succesfully'
    
    def reset(self):
        self.__init__(self.configdata, self.mqtt)
        self.status = "reset"
        self.publish()
        
    async def startgame(self):
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
        await self.holeroutine()
        for hole in self.holes:
            hole.off()
        self.state = 'end'
        if not self.shutdown_request:
            self.command = 'standby'
            self.reset()
        else:
            self.state = 'shutting down'
        return 'game end'
    
    async def holeroutine(self):
        for hole in self.holes:
            hole.running = True
        holetasks = [hole.set() for hole in self.holes]
        asynctasks = asyncio.gather(*holetasks)
        try:
            await asyncio.wait_for(self.game_interrupt(), timeout=self.gametime)
        except asyncio.TimeoutError:
            logging.info('Game ran to completion')
        for hole in self.holes:
            hole.running = False
        asynctasks.cancel()

        
    def colour_detected(self, detected_colour):
        for hole in self.holes:
            if hole.colour == detected_colour:
                hole.interruptFlag = True
    
    def publish(self):
        self.mqtt.publish('game/status', json.dumps({k:self.__dict__[k] for k in self.mqtt_attributes}))
    
    async def standby(self):
        self.state = 'standby'
        self.publish()
        time.sleep(1)
        return self.state
    
    def quit(self):
        self.state = 'off'
        self.publish()
        return self.state
    
    async def game_interrupt(self):
        while not (self.shutdown_request):
            await asyncio.sleep(0)
        logging.debug('Game was terminated prematurely')

    def switch_event(self, id, colour, **kwargs):
        """

        :param id: ID of the switch that was hit
        :param colour: colour of the hole at the time the switch was fired
        """
        # note the ID in the MQTT message runs 1 to n, where as the index into the array starts
        # from zero
        if colour == "off":
            self.score += self.hole_scores[id-1]
        elif colour in self.colours:
            # double points if the hole was lit at the time
            self.score += self.hole_scores[id - 1] * 2

        else:
            logging.error(f'unhandled colour:{colour}')




    @property
    def difficulty(self) -> int:
        """
        The game difficulty from the configuration file
        """
        return int(self.configdata['difficulty'])

    @property
    def nHoles(self) -> int:
        """
        The number of holes from the configuration file
        """
        return int(self.configdata['nHoles'])

    @property
    def holeconfig(self) -> dict:
        """
        Hole configuration from the configuration file
        """
        return self.configdata['holeconfig']

    @property
    def gametime(self) -> int:
        """
        Game time from the configuration file
        :return:
        """
        return self.configdata['gametime']

    @property
    def colours(self) -> list(str):
        """
        Colour to be used by the game from the configuration file
        """
        return self.configdata['colours']

    @property
    def hole_scores(self) -> list[int]:
        """
        hole scores from the configuration file
        """
        return self.configdata['hole_scores']

        
                
class _GameHole:
    """
    Hole
    """
    mqtt_attributes = ["status", "offtime", "id", "colour" ]
    
    def __init__(self, id, status, mqtt, holeconfig, colour_list):
        self.id = id
        self.status = status
        self.running = False
        self.offtime = 0
        self.abs_offtime = 0
        self.mqtt = mqtt
        self.colour = colour_list[0]

        self.holeconfig = holeconfig
        self.colour_list = colour_list

        self.taskname = None

        self.publish()
        self.interruptFlag = False
        self.overrideFlag = False
 
    async def main(self):
        await self.set()
             
    async def set(self, sleepTime=1):
        while self.running:
            self.taskname = asyncio.current_task()
            if random.random() <= self.probOn: 
                self.status = True
                self.colour = random.choice(self.colour_list)  
                if not self.overrideFlag:
                    sleepTime = random.uniform(*self.onRange)
            else:
                self.status = False
                if not self.overrideFlag:
                    sleepTime = random.uniform(*self.offRange)
            self.offtime = sleepTime
            self.overrideFlag = False
            self.interruptFlag = False
            await self.asyncpublish()
            try:
                await asyncio.wait_for(self.hole_interrupt(), timeout=sleepTime)
            except asyncio.TimeoutError:
                logging.debug('Hole ' + str(self.id) + ' was not interrupted')
            except asyncio.CancelledError:
                logging.debug('Hole task ' + str(self.id) + ' was cancelled')
          
    async def hole_interrupt(self):     
        while not (self.interruptFlag):
            #logging.debug(str(self.id) + ' interrupt loop')
            await asyncio.sleep(0)     
        logging.debug('Hole ' + str(self.id) + ' was interrupted')
        self.overrideFlag = True
               
                          
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

    @property
    def onRange(self) -> tuple(int, int):
        """
        range of time the hole can be illuminated for
        """
        return self.holeconfig['min_on_time'], self.holeconfig['max_on_time']

    @property
    def offRange(self) -> tuple(int, int):
        """
        range of time the hole off between illumination
        """
        return self.holeconfig['min_off_time'], self.holeconfig['max_off_time']

    @property
    def probOn(self) -> float:
        """
        probability the hole is illuminated 0 to 1
        """
        return self.holeconfig['prob_on']