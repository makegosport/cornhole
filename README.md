# MAKE Game - Internet of Beanbags
A containerized framework for the MAKE beanbag game.
## Requirements
### Docker
This *should* run on anything any modern OS, Windows / MacOS / Linux (including ARM devices *e.g.* RPi). You will need a container runtime installed on the device along with Docker-Compose. Installation instructions for Docker can be found [here](https://docs.docker.com/get-docker/). Windows install comes with Docker-Compose, for linux you'll need to install it seperately. No idea about MacOS. This should also run on Podman though I haven't tried it. 
### Git
Not strictly a requirement, but will make getting all of the files from here to your machine much easier! Installation instructions are [here](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
## Installation
You will first need to download the code. If you have git installed just run 
```
git clone https://github.com/makegosport/cornhole`
```
from a terminal window whilst in a directory you'd like to put it. 
For example on windows:
* Press Win+R and type `cmd` or use a terminal window from [VSCode](https://code.visualstudio.com/)
* You should be in you're home director already so make a new folder with `mkdir code`
* Clone the github repo with the command `git clone https://github.com/makegosport/cornhole`
## Running
Once you have completed the above it is a simple as running (either from a terminal or a VSCode terminal)
`docker-compose up`
This may take a few minutes the first time you run it whilst it downloads a couple of extra things. Keep an eye on the output for any error messages. If you have any services running on the machine that use port 80, or port 1883, you may have some issues. These ports can be remapped in the [docker-compose.yml](docker-compose.yml) file. To stop the stack use `Ctrl + C` If you make any changes to the main game python files you will need to force a rebuild with ```docker-compose up --build```

Once you see `Connected with result code 0` everything has loaded successfully. You can confirm by running the command `docker ps` in another terminal window/tab and you should see 3 containers with a status of `up`. 

You can now go to either:
* [http://127.0.0.1/ui](http://127.0.0.1/ui) To see the sample user interface
* [http://127.0.0.1/](http://127.0.0.1/) To see the Node-Red instance that's creating the UI. 

## Contributing
As you will see the MQTT broker is acting as the central orchestrator for the lights, scoring and game. There are several tasks/improvements that need to be made (with accompanying pseudocode):
* A hardware interrupt handler to detect bean bag scoring events.:
``` 
if GPIO_0 is low{
    mqtt_publish("hole 0 scored")
}
```
* Integration of the colour detection scheme. The aspiration is that a webcam facing the player will detect the colour of bean bag they're holding a act against the player
```
if colour_detector(red) is True{
    mqtt_publish({"player_bag", "red"})
}
```
* Driving the light controller: The easiest solution at the moment is to have a seperate ESP devices running [WLED](https://kno.wled.ge/). We can either subscribe the ESP to the MQTT broker directly (easyish) or parse the MQTT into API calls (harder but better as this will allow access to the pre-programmed lighting effects)
```
mqtt_subscribe(hole/1/colour)
on_message(
    curl POST wled.ip desired_colour_and_effect.json
)
```
* Connecting with Social/Cheerlights
Using [krcb197's twitter api](https://github.com/krcb197/CheerLightTwitterAPI/)

Other less developed aspirations:
* Seperate UI for player and game 'staff'
* Persistant scoreboard (maybe with publishing to web?)
* Dynamic game difficulty


