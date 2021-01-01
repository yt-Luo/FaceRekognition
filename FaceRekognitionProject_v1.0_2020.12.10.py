# -*- coding: utf-8 -*-
"""
Created on Thu Dec 10 12:59:07 2020

@author: Acer
"""

import boto3

ACCESS_KEY = 'ASIA2GZQNLHX6GKDYCRG'
SECRET_KEY = 'DxlsF3/nnOPTKImdFZrEdNGioyYvbmBk8pavEtN6'
SESSION_TOKEN = 'FwoGZXIvYXdzENL//////////wEaDAhoyBsX0p7dB4YkWCK1AWFr+DDY91nkHPxmlR/Br7x6QPQDPEK3DudRRuGYMDKjAhlZV62EK15LcRbpKZZG6Tj7JXYaTnATR87x8uXoMyhEykpr0n3X+Kr1mkEc4ArLNGNWeZebbMQigNP5dde9SZSDc2YfK3aTZeha+LhOALlZwVuQaipnn7hcyyUmFngWM+WNuB8cvg0KWHTgdgKevQk/Ay+MYesSkrtWdAZpZzEE/M6oEdF1wHT62p0UaNdWLfPuzt0o8YnC/gUyLSsdxaWFCFXuJsq69CLUTc6kzy+1gmc7ut8om+f4KiEp0t3Jx6j5KQFSHvariA=='


s3_client = boto3.client(
    's3',                                    
                  aws_access_key_id=ACCESS_KEY,
                  aws_secret_access_key=SECRET_KEY,
                  aws_session_token=SESSION_TOKEN
)                                                    

collectionId='mycollection' #collection name

rek_client=boto3.client('rekognition', region_name='us-east-1',  #region name
                        aws_access_key_id=ACCESS_KEY,
                        aws_secret_access_key=SECRET_KEY,
                        aws_session_token=SESSION_TOKEN)


bucket = 'wenb' #S3 bucket name
all_objects = s3_client.list_objects(Bucket = bucket )   #s3內的物件


'''
delete existing collection if it exists
'''
list_response=rek_client.list_collections(MaxResults=2)

if collectionId in list_response['CollectionIds']:

    rek_client.delete_collection(CollectionId=collectionId)

'''
create a new collection 
'''
rek_client.create_collection(CollectionId=collectionId)

'''
add all images in current bucket to the collections
use folder names as the labels
'''

for content in all_objects['Contents']:
    collection_name,collection_image =content['Key'].split('/')
    if collection_image:
        label = collection_name
        print('indexing: ',label)
        image = content['Key']    
        index_response=rek_client.index_faces(CollectionId=collectionId,
                                Image={'S3Object':{'Bucket':bucket,'Name':image}},
                                ExternalImageId=label,
                                MaxFaces=1,
                                QualityFilter="AUTO",
                                DetectionAttributes=['ALL'])
        print('FaceId: ',index_response['FaceRecords'][0]['Face']['FaceId'])
        
        
import cv2
#import time
import boto3
import datetime
    
cap = cv2.VideoCapture(0)

while(True):
  ret, frame = cap.read()
  cv2.imshow('frame', frame)
  if cv2.waitKey(1) & 0xFF == ord('1'): #拍照按1
     now = datetime.datetime.now()
     nowtime = now.strftime("%Y-%m-%d.%H.%M")
     cv2.imwrite(nowtime+'.jpg', frame)
     break

cap.release()
cv2.destroyAllWindows()

while True:
        #camera warm-up time
        #time.sleep(2)
        
        image =nowtime+'.jpg'       
        print('captured '+image)
        with open(image, 'rb') as image:
            try: #match the captured imges against the indexed faces
                match_response = rek_client.search_faces_by_image(CollectionId=collectionId, Image={'Bytes': image.read()}, MaxFaces=1, FaceMatchThreshold=85)
                if match_response['FaceMatches']:
                    print('歡迎您來上課！',match_response['FaceMatches'][0]['Face']['ExternalImageId'], '已簽到')
                    print('Similarity: ',match_response['FaceMatches'][0]['Similarity'], '%')
                    print('Confidence: ',match_response['FaceMatches'][0]['Face']['Confidence'], '%')
                    nowtime1 = now.strftime("%Y年%m月%d日%H點%M分")
                    print('您的簽到時間為', nowtime1) 

                    break
                else:
                    print('No faces matched')
                    break
            except:
                print('No face detected')
                break
            
    