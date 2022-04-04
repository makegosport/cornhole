from chardet import detect
from cv2 import WINDOW_NORMAL
import paho.mqtt.client as mqtt
import yaml
import time
import logging.config
import uuid
import colorsys
import cv2
import numpy as np
import sys
import time
from collections import deque
from os.path import exists
import json

cv2.Tracker
def readconfigfile(inputfile):
    logging.info("Reading config file: config.yaml")
    with open(inputfile, "r") as configfile:
        try:
            config = yaml.safe_load(configfile)
            logging.debug('Load Conf File')
            mqttbroker = config['mqttbroker']
            logging.debug('Read mqttbroker')
            detectorconf = config['detector']
            logging.debug('Read detector')
            logconf = config['logs']
            logging.debug('Read Logs')
        except Exception as e:
            logging.error(e)
    logging.debug(configfile)
    return mqttbroker, detectorconf, logconf


#MQTT client callback Functions

# Callback Functions - called on mqtt connection events
# callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    global newgame
    if rc == 0:
        logging.info("Successfully connected to broker")
    print("Connected with result code "+str(rc))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("detector/#")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    global newgame
    msg.payload = str(msg.payload.decode("utf-8"))
    logging.debug(msg.topic+" "+msg.payload) 

if exists('detector/config.yaml'):
    conf_file = 'detector/config.yaml'
elif exists('config.yaml'):
    conf_file = 'config.yaml'
else:
    logging.error("Cannot find config file")
    quit()
mqttbroker, detectorsettings, logconf = readconfigfile(conf_file)

#configure logging
logconf = {
    'version': 1,
    'loggers': {
        'root': logconf
    }
}
logging.config.dictConfig(logconf)

#Parse command line arguments (e.g. to determine if running in Docker stack)
inDocker = False
if len(sys.argv) > 1:
    if sys.argv[1] == 'docker':
        inDocker = True
        mqttbroker['broker'] = 'broker'
        logging.info('Docker mode requested')

#MQTT Client Configuration
client = mqtt.Client(str(uuid.uuid4())+'colour_detector')
client.on_connect = on_connect
client.on_message = on_message
logging.debug("Defining connection to broker")
client.connect_async(mqttbroker['broker'], mqttbroker['port'], mqttbroker['KeepAlive'])


#Threaded MQTT handler
if inDocker:
    logging.info("Starting connection, waiting for 5 seconds for broker to spawn")
    time.sleep(5)
else:
    logging.info("Starting connection: Ensure that your MQTT broker is running at " + str(mqttbroker['broker']) + ":" + str(mqttbroker['port']))
print('Starting MQTT listener')
print(client)

#Init the detector
if detectorsettings['use_webcam']:
    image_source = cv2.VideoCapture(0)
else:
    try:
        image_source = cv2.imread(detectorsettings['image_file'])
    except FileNotFoundError:
        logging.error('File ' + detectorsettings['image_file'] + ' not found')

#Read Colourmaps
colour_map = detectorsettings['colours']
logging.info(colour_map) 


def click_event(event, x, y, flags, param):
    global shutdown
    if event == cv2.EVENT_LBUTTONDOWN:
        clicked_colour = frame[y,x]
        logging.debug('Clicked colour: '+ str(clicked_colour))

def trackbar_callback(value):
    pass    

def create_colour_arrays(val):   
    hUpper = val['h_cen'] + val['h_tol']
    hLower = val['h_cen'] - val['h_tol']
    splitmask = False
    if hUpper > 179:
        hUpper -= 179
        splitmask = True
    elif hLower < 0:
        hLower += 179
        splitmask = True
    s_min = val['s_min']
    v_min = val['v_min']
    s_max = 255
    v_max = 255
    val['splitmask'] = splitmask
    if splitmask:
        val['limits'] = {
            'lower': np.array([hLower, s_min, v_min]),
            'upper': np.array([179, s_max, v_max]),
            'lower1': np.array([0, s_min, v_min]),
            'upper1': np.array([hUpper, s_max, v_max])   
        }
    else:
        val['limits'] = {
            'lower': np.array([hLower, s_min, v_min]),
            'upper': np.array([hUpper, s_max, v_max])
        }
    val['bgr'] = colorsys.hsv_to_rgb(val['h_cen'] / 180, 1, 1)
    val['bgr'] = tuple(int(x * 255) for x in reversed(val['bgr']))
    return val

def cal_colour(state, userdata):
    print(str(state) + state(userdata))
# Headless?
if not detectorsettings['headless']:
    cv2.namedWindow('DetectorUI')
    cv2.namedWindow('Controls', flags=WINDOW_NORMAL)
    cv2.resizeWindow('Controls', 640, 700)
    cv2.namedWindow('DetectedImage')
    headless = False
else:
    headless = True


#Initial Detector Settings
for col_name, colour in colour_map.items():
    for key, val2 in colour.items():
        if key == 'h_cen':
            maxV = 179
        elif key =='h_tol':
            maxV = 89
        else:
            maxV = 255
        cv2.createTrackbar(col_name + ' ' + key, 'Controls', val2, maxV, trackbar_callback)
    colour = create_colour_arrays(colour)

#tracker = cv2.legacy.TrackerKCF_create()
#initBB = None
#fps = None

client.loop_start()
shutdown = False 
cv2.setMouseCallback('DetectorUI', click_event) 

while not shutdown:
    foundobjects = {}
    if cv2.waitKey(1) == 27:
        break
    ret, frame = image_source.read()
    if not ret:
        logging.error('Video device unavailable')
        break
    #Read Inputs
    for col_name, colour in colour_map.items():
        for key in ['h_cen', 'h_tol', 's_min', 'v_min']:
            colour[key] = cv2.getTrackbarPos(col_name + ' ' + key, 'Controls')
        colour = create_colour_arrays(colour)
    hsv_image = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    for col_name, colour in colour_map.items():
        colour['mask0'] = cv2.inRange(hsv_image, colour['limits']['lower'], colour['limits']['upper'])
        if colour['splitmask']:
            colour['mask1'] = cv2.inRange(hsv_image, colour['limits']['lower1'], colour['limits']['upper1'])
            colour['mask'] = colour['mask1']
        else:
            colour['mask'] = colour['mask0']
        colour['filtered'] = cv2.bitwise_and(frame, frame, mask=colour['mask'])
        contours, hierarch = cv2.findContours(colour['mask'],
                                              cv2.RETR_EXTERNAL,
                                              cv2.CHAIN_APPROX_SIMPLE)[-2:]
        for pic, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            if(area > 200 and area < 800):
                logging.debug(col_name + ' object spotted')
                x, y, w, h = cv2.boundingRect(contour)
                foundobjects[col_name + str(pic)] = {
                        'colour'    :   col_name,
                        'pos'       :   (x + (w//2), y + (h//2)),
                        'size'      :   area,     
                }
                frame = cv2.rectangle(frame, (x, y),
                                      (x + w, y + h),
                                      (colour['bgr']), 2)
                cv2.imshow('DetectedImage', frame)
                client.publish("detector/object", json.dumps(foundobjects))
                 
        cv2.imshow('DetectorUI', frame)



#Init Detector Thread

image_source.release()
cv2.destroyAllWindows()

client.loop_stop
print('Detector shutdown complete')