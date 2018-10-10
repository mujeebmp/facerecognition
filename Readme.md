Project Title
This is a human face, emotion and aga detection software by using OpenCV, Amazon Recokgnition, Amazon S3, Amazon db. The software use raspberry pi hardware and raspberri pi standard camera

Getting Started
Install OpenvCV 2.0 in raspberry pi. Connect camera, use below script to check camera working or not
from picamera import PiCamera
from time import sleep

camera = PiCamera()

camera.start_preview()
while(1):
    sleep(10)    
camera.stop_preview()


Prerequisites
OpenCV 2.0
Amazon Rekognition account, Amazon S3 account, Amazone dynamo db account

