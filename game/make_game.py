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
import paho.mqtt.client as mqtt
from math import floor

class MakeGame:
    """
    Main Game Class

    Args:
        configdata: data from the configuration file
        mqtt_client: mqtt client instance

    """
    def __init__(self, configdata, mqtt_client: mqtt.Client):

        mqtt_attributes = ["status", "score", "colours", "nHoles", "difficulty", "gametime", "score", "start_time", "finish_time", "rel_time", "user", 'remain_time', 'seconds_remaining']
        self.score = 0
        self.configdata = configdata
        self.shutdown_request = False
        self.command = 'standby'
        self.status = "off"
        self._twitter_follower = False
        self.mqtt:mqtt.Client = mqtt_client
        self.holes = [_GameHole(id=x + 1,
                                status=False,
                                mqtt_client=self.mqtt,
                                holeconfig=self.holeconfig,
                                colour_list=self.colours) for x in range(self.nHoles)]
        self.basic_points = [int(x) for x in configdata['hole_scores']]
        self.bonus_multiplier = int(configdata['bonusMult'])
        self.start_time = None
        self.finish_time = None
        self.rel_time = None
        self.hole_lt = 1
        self.hole_ut = 5
        self.shutdown_request = False
        self.command = 'standby'
        self._username = 'anon'
        self.remain_time = None
        self.seconds_remaining = self.gametime
        self.score_event = None

        self.publish()

    def update_time(self):
        oldtime = self.seconds_remaining
        self.remain_time = max(self.finish_time - time.time(),0)
        self.seconds_remaining = max(floor(self.finish_time - time.time()),0)
        if self.seconds_remaining == oldtime:
            return False
        else:
            return True
    
       
    async def main(self):
        while True:
            if self.command == 'standby':
                await self.standby()
            elif self.command == 'run':
                await self.startgame()
    
    def reset(self):
        self.__init__(self.configdata, self.mqtt)
        self.status = "reset"
        self.publish()
        
    async def startgame(self):
        self.start_time = time.time()
        self.finish_time = time.time() + self.gametime
        self.rel_time = time.time() - self.start_time
        logging.info(f'{self.start_time=:.1f}, {self.finish_time=:.1f}')
        self.update_time()
        self.status = "starting"
        self.publish()
        for hole in self.holes: #Turn all holes off at start of game
            hole.off()
        self.status = "playing"
        self.publish()
        await self.holeroutine()
        for hole in self.holes:
            hole.off()
        self.scoreboard()
        self.status = "end"
        self.publish()
        self.command = 'standby'
        self.reset()
        return 'game end'
    
    async def holeroutine(self):
        for hole in self.holes:
            hole.running = True
        holetasks = [hole.set() for hole in self.holes]
        asynctasks = asyncio.gather(*holetasks)
        shutdown = False
        while not shutdown:
            try:
                if self.update_time():
                    self.publish()
                shutdown = await asyncio.wait_for(self.game_interrupt(), timeout=self.remain_time)
                #shutdown = await asyncio.wait_for(self.game_interrupt(), timeout=3)
            except asyncio.TimeoutError:
                logging.info('Game ran to completion')
                shutdown = True
                break
        for hole in self.holes:
                hole.running = False
        asynctasks.cancel()

    def switchevent(self, msg):
        logging.debug('Switch Event')
        self.bonusFlag = False
        switchdata = json.loads(msg.payload)
        switchdata['id'] = int(msg.topic[-1]) - 1
        if switchdata['colour'] != 'off':
            self.holes[switchdata['id']].interruptFlag = True
            self.bonusFlag = True
        self.score_event = switchdata['id']
    
    def publish(self):

        status_dict = {'status': self.status,
                       'raw_score': self.score,  # the raw score is the point accumulated with
                                                 # hits on holes, the score includes any
                                                 # bonus multipliers
                       'start_time': self.start_time,
                       'finish_time': self.finish_time,
                       'rel_time': self.rel_time,
                       'username': self.username,
                       'seconds_remaining': self.seconds_remaining
        
                       }

        if self.twitter_follower:
            status_dict['score'] = self.score * 2
        else:
            status_dict['score'] = self.score

        payload = json.dumps(status_dict)

        self.mqtt.publish('game/status', payload)
    
    def scoreboard(self):
        self.mqtt.publish('game/leaderboard', payload=json.dumps({
            'user': self._username,
            'score': self.score,
            'twitter_follower': self._twitter_follower
        }))
        
    async def standby(self):
        self.state = 'standby'
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
    def colours(self) -> list[str]:
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

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, value: str):
        self._username = value

    @property
    def twitter_follower(self) -> bool:
        return self._twitter_follower

    @twitter_follower.setter
    def twitter_follower(self, value:bool):
        self._twitter_follower = value
        
    async def game_interrupt(self):       
        if self.shutdown_request:
            logging.debug('Game was terminated prematurely')
            return True
        elif self.score_event != None:
            self.score += (self.basic_points[self.score_event] * (self.bonus_multiplier * self.bonusFlag))
            self.publish()
            self.score_event = None
            self.bonusFlag = False
            return False
        elif self.remain_time <= 0:
            return True
               
                
class _GameHole:

    """
    Hole
    """
    mqtt_attributes = ["status", "offtime", "id", "colour" ]
    
    def __init__(self, id, status:bool, mqtt_client: mqtt.Client, holeconfig: dict,
                 colour_list: list[str]):

        self.id:int = id
        self.status:bool = status
        self.running = False
        self.offtime = 0
        self.abs_offtime = 0
        self.mqtt:mqtt.Client = mqtt_client
        self.colour = colour_list[0]
        self.holeconfig = holeconfig
        self.colour_list = colour_list

        self.taskname = None

        self.publish()
        self.interruptFlag = False
        self.overrideFlag = False

 
    # async def main(self):
    #     await self.set()
             
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
    def onRange(self) -> tuple[int, int]:
        """
        range of time the hole can be illuminated for
        """
        return self.holeconfig['min_on_time'], self.holeconfig['max_on_time']

    @property
    def offRange(self) -> tuple[int, int]:
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