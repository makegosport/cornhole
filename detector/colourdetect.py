from re import U
import cv2
import numpy as np

#cam = cv2.VideoCapture(0)
def nothing(x):
   pass
cam = cv2.imread('cornhole/cornhole.jpg')
cv2.namedWindow('cornhole')

cv2.createTrackbar('Blue Min', 'cornhole', 0, 179, nothing)
cv2.createTrackbar('Blue Max', 'cornhole', 0, 179, nothing)
cv2.createTrackbar('Red Min', 'cornhole', 0, 179, nothing)
cv2.createTrackbar('Red Max', 'cornhole', 0, 179, nothing)

cv2.setTrackbarPos('Blue Min', 'cornhole', 101)
cv2.setTrackbarPos('Blue Max', 'cornhole', 150)
cv2.setTrackbarPos('Red Min', 'cornhole', 170)
cv2.setTrackbarPos('Red Max', 'cornhole', 179)
while True:
    if cv2.waitKey(1) == 27:
        break
#    ret, frame = cam.read()
    cam = cv2.imread('cornhole/cornhole.jpg')
    frame = cam
    Bmin = int(cv2.getTrackbarPos('Blue Min', 'cornhole'))
    Bmax = int(cv2.getTrackbarPos('Blue Max', 'cornhole'))
    Rmin = int(cv2.getTrackbarPos('Red Min', 'cornhole'))
    Rmax = int(cv2.getTrackbarPos('Red Max', 'cornhole'))


    into_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    BL_limit = np.array([Bmin,50,50])
    BU_limit = np.array([Bmax,255,255])
    RL_limit = np.array([Rmin,60,60])
    RU_limit = np.array([Rmax,255,255])
    
    kernal = np.ones((10,10), "uint8")
    
    b_mask = cv2.inRange(into_hsv,BL_limit,BU_limit)
    r_mask = cv2.inRange(into_hsv,RL_limit,RU_limit)
    #b_mask = cv2.dilate(b_mask, kernal)
    #r_mask = cv2.dilate(r_mask, kernal)
    blue = cv2.bitwise_and(frame,frame, mask=b_mask)
    red = cv2.bitwise_and(frame,frame, mask=r_mask)


    contours, hierarchy = cv2.findContours(r_mask,
                                           cv2.RETR_TREE,
                                           cv2.CHAIN_APPROX_SIMPLE)
      
    for pic, contour in enumerate(contours):
        area = cv2.contourArea(contour)
        if(area > 500):
            x, y, w, h = cv2.boundingRect(contour)
            frame = cv2.rectangle(frame, (x, y), 
                                       (x + w, y + h), 
                                       (0, 0, 255), 2)
              
            cv2.putText(frame, "Red Colour", (x, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0,
                        (0, 0, 255))  

    contours, hierarchy = cv2.findContours(b_mask,
                                           cv2.RETR_TREE,
                                           cv2.CHAIN_APPROX_SIMPLE)    
    for pic, contour in enumerate(contours):
        area = cv2.contourArea(contour)
        if(area > 500):
            x, y, w, h = cv2.boundingRect(contour)
            frame = cv2.rectangle(frame, (x, y),
                                       (x + w, y + h),
                                       (255, 0, 0), 2)
              
            cv2.putText(frame, "Blue Colour", (x, y),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1.0, (255, 0, 0))
              
    cv2.imshow("Multiple Color Detection in Real-TIme", frame)    
    cv2.imshow("Mask B", blue)
    cv2.imshow("Mask R", red)
    
#cam.release()

cv2.destroyAllWindows
    