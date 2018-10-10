#!/usr/bin/python
from picamera.array import PiRGBArray
from picamera import PiCamera
import time
import cv2
import sys
import boto3
import os
import subprocess
from botocore.client import ClientError


faceCascade = cv2.CascadeClassifier('/home/pi/opencv-3.0.0/data/haarcascades/haarcascade_frontalface_alt.xml')

# initialize the camera and grab a reference to the raw camera capture
camera = PiCamera()
camera.resolution = (640, 480)
camera.framerate = 30
rawCapture = PiRGBArray(camera, size=(640, 480))

s3client = boto3.client('s3')
s3resource = boto3.resource('s3')
dbclient = boto3.resource('dynamodb')
table = dbclient.Table('FacecollectionSL01')
client = boto3.client('rekognition','eu-west-1')



firsttimeflag = True

bucket_name = 'bucketforrekognition'


#client.delete_collection(CollectionId = 'myhomephotos')
#client.create_collection (CollectionId = 'myhomephotos')


# capture frames from the camera

for frame in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):

	# grab the raw NumPy array representing the image, then initialize the timestamp
	# and occupied/unoccupied text
    
    image = frame.array
    
	#convert to gray scale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
	#this is for motion detection by comparing previus image, firsttimeflag is to skip the very first image
    if firsttimeflag == False:
        
		#taking diff for motion detection
        difference = cv2.absdiff(prv_gray_image,gray)
		

        rv,dt=cv2.threshold(difference,35,255,cv2.THRESH_BINARY) # Set a threshold for B/W

        nuwhitedots = cv2.countNonZero(dt)
           
		#number of whitedots with previuse image, get motion
        if nuwhitedots >150:
            print "Motion detected, searching for face"
            
            # Detect faces in the image
			#use open cv face detection first
			
            faces = faceCascade.detectMultiScale(gray,1.1, 5)

            if len(faces) >0:

            print "Face detected"
                #save image to local drive    
                filename = '/home/pi/FaceDetectedImage/detected_image'

                filename=filename+str(int(time.time()*1000000))+".png"

                cv2.imwrite(filename,image)

                bucketkey="detected_image"+str(int(time.time()*1000000))+".png"
				
				#upload to amazon bucket

                s3client.upload_file(filename, bucket_name, bucketkey)

                print "File uploaded"
                                

                indexresponse=client.index_faces(
        				    CollectionId='myhomephotos',
                                            DetectionAttributes=['ALL'],
       				    Image= {
      				    'S3Object': {
  			              'Bucket': bucket_name,
  			              'Name': bucketkey
  			              }})
                print "Face indexed"
                
                if len (indexresponse['FaceRecords'])>=1:

                    print ("Face recognised")
                    faceid = indexresponse['FaceRecords'][0]['Face']['FaceId']
                    #print faceid
                    gender = indexresponse['FaceRecords'][0]['FaceDetail']['Gender']['Value']
                    print (" Gender :")
                    print (gender)
                    emotion = indexresponse['FaceRecords'][0]['FaceDetail']['Emotions'][0]['Type']
                    print (" Emotion : ")
                    print (emotion)
                    age = indexresponse['FaceRecords'][0]['FaceDetail']['AgeRange']['High']
                    print ("Age :")
                    print (age)

                    #Add current detected face to data base
                    response = table.put_item(
                                                    Item={
                                                     'FaceID': faceid,
                                                     'Gender': gender,
                                                     'Age': age,
                                                     'Alert':'true',
                                                     'ImageName':bucketkey,
                                                     'FaceName':'None',
                                                     'Emotion':'Happy',
                                                    })

                    print ("Value added to database")
                    
                    searchresponse = client.search_faces(
                           CollectionId = 'myhomephotos',
                           FaceId= faceid,
                           FaceMatchThreshold=90,
                           MaxFaces=5,
                           )
                    for s in range(0,len(searchresponse['FaceMatches'])):
                        if(searchresponse['FaceMatches'][s]['Similarity'])>90:
                            print (searchresponse['FaceMatches'][s]['Face']['FaceId'])
                            response = table.get_item(
                                                   Key={
                                                    'FaceID': searchresponse['FaceMatches'][s]['Face']['FaceId'],
                                                      })

                            tablelen= response['ResponseMetadata']['HTTPHeaders']['content-length']
                            if len(tablelen)>2:
                               if response['Item']['FaceName'] != "None":
                                  print response['Item']['FaceName']
                                    
									#Add the name of the person in database manually
                                    #add name to current face in database
                               table.update_item(
                                               Key={
                                                'FaceID': faceid,
                                                      },
                                        UpdateExpression='SET FaceName = :val1',
                                        ExpressionAttributeValues={
                                            ':val1': response['Item']['FaceName']  })

                               else:
                                    print ("No Name in database")                          
    else:
        firsttimeflag=False

    #store previus image for motion detection

    prv_image = image.copy()
    prv_gray_image = cv2.cvtColor(prv_image, cv2.COLOR_BGR2GRAY)

    # show the frame
    cv2.imshow("Frame", image)

    key = cv2.waitKey(1) & 0xFF

	# clear the stream in preparation for the next frame
    rawCapture.truncate(0)

	# if the `q` key was pressed, break from the loop
    if key == ord("q"):
        break