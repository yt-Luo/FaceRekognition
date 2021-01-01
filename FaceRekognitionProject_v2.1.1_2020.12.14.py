#!/usr/bin/env python
# coding: utf-8

# In[ ]:


'''臉部辨識簽到退
功能: 比對本地照片與s3照片集合，確認是否有此人存在，並紀錄簽到退時間

'''
# In[ ]:


#pip install boto3


# In[ ]:


#pip install opencv-python


# In[ ]:


import boto3
import cv2
import boto3
import datetime


# In[ ]:

# Noted: session time
ACCESS_KEY = 'ASIASVAWICX3MXDNLIGK'
SECRET_KEY = '5MNlaoqqN2fQUTax2YRdTO8j28JNK6vqcW7in5eK'
SESSION_TOKEN = 'FwoGZXIvYXdzEEoaDOWEIAXy1z5kbRrjGSK1AaE7CIuqKQkbQNYNCVQLSpNxRs1+UbTMPFTNWeY3bgS7HZ+irqBg3WKrWhKQH1G6P8UcH7vqL975vPV8PTr8XY52JK8tipMvZx6JGz4BDb58B1tyKRtUASWGSiVIX0jVFdUGdjINd+KlWIu0dC16yHLBGBGAZKuv8C5hAJyTRKMC+FuOsGLQpveNUllK1wiZ0uRp1C9/DyP22czip+2+Ofa8JIj3hAtPjzLQbm/QWxo07BmRcecojMjc/gUyLV0gGX2+/1cF32LT+fahmmj9sPEJgMy4THB49c5KyfW3eFdaMH/tp2jsIB7oUQ=='


# In[ ]:


# 自訂
bucket = 'facialanalysisproject' #S3 bucket name

collectionId='mycollection' #collection name


# In[ ]:


#連上AWS服務: s3, rekognition
s3_client = boto3.client('s3',aws_access_key_id=ACCESS_KEY, 
                         aws_secret_access_key=SECRET_KEY, 
                         aws_session_token=SESSION_TOKEN)                                                    

rek_client=boto3.client('rekognition', region_name='us-east-1', 
                        aws_access_key_id=ACCESS_KEY, 
                        aws_secret_access_key=SECRET_KEY,
                        aws_session_token=SESSION_TOKEN)

collectionId='mycollection' #collection name

bucket = 'facialanalysisproject' #S3 bucket name


# In[ ]:

#將s3上的照片指向要辨識的集合
def index_face():
    # delete existing collection if it exists
    list_response=rek_client.list_collections(MaxResults=2)
    
    if collectionId in list_response['CollectionIds']:
        rek_client.delete_collection(CollectionId=collectionId)
    
    # create a new collection
    rek_client.create_collection(CollectionId=collectionId)
    
    # add all images in current bucket to the collections    
    all_objects = s3_client.list_objects(Bucket = bucket )   # 列出s3內的所有物件
    
    for content in all_objects['Contents']:
        collection_name,collection_image = content['Key'].split('/')
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
        
#index_face()    


# In[ ]:

#照相
def camera():
    print("開啟相機，請按q拍照")
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW) #開啟第一台相機  cv2.CAP_DSHOW 解決openCV的ERROR
    while(True):
        ret, frame = cap.read() #捕獲一幀影象。ret代表成功與否（True 代表成功，False 代表失敗）。frame 就是攝影機的單張畫面
        cv2.imshow('frame', frame) # 顯示圖片
        if cv2.waitKey(1) & 0xFF == ord('q'):  # 按q拍照 #ord('q')如果按鍵為q，退出迴圈
            #waitKey(1) 中的數字代表等待按鍵輸入之前的無效時間，單位為毫秒，在這個時間段內按鍵 ‘q’ 不會被記錄，在這之後按鍵才會被記錄，並在下一次進入if語段時起作用。也即經過無效時間以後，檢測在上一次顯示影象的時間段內按鍵 ‘q’ 有沒有被按下，若無則跳出if語句段，捕獲並顯示下一幀影象。
            now = datetime.datetime.now()
            nowtime = now.strftime("%Y-%m-%d_%H.%M.%S")
            image_name = nowtime+'.jpg'
            cv2.imwrite(image_name, frame)  # 存檔，檔案名稱為拍照時間
            break
    cap.release() # 釋放攝影機
    cv2.destroyAllWindows() # 關閉所有 OpenCV 視窗
    return image_name, now
#camera()


# In[ ]:

#state = 簽到 or 簽退
def sign(state):
    index_face()
    image_name, now = camera()
    while True:      
        print('captured '+image_name)
        with open(image_name, 'rb') as image:
            try: #match the captured imges against the indexed faces
                match_response = rek_client.search_faces_by_image(CollectionId=collectionId, Image={'Bytes': image.read()}, MaxFaces=1, FaceMatchThreshold=85)
                if match_response['FaceMatches']:
                    print('歡迎您來上課！' if state == '簽到' else '簽退成功，可以下課回家了~',match_response['FaceMatches'][0]['Face']['ExternalImageId'], '已'+state)
                    print('Similarity: ',match_response['FaceMatches'][0]['Similarity'], '%')
                    print('Confidence: ',match_response['FaceMatches'][0]['Face']['Confidence'], '%')
                    print('您的'+state+'時間為', now.strftime("%Y年%m月%d日%H點%M分"))
                    uploaded = upload_to_aws(image_name, bucket, match_response['FaceMatches'][0]['Face']['ExternalImageId'] +'/'+ image_name)
                    break
                else:
                    print('No faces matched')
                    break
            except:
                print('No face detected')
                break
#sign('簽到')
#sign('簽退')


# In[ ]:


# 上傳檔案到s3的folder裡
from botocore.exceptions import NoCredentialsError
def upload_to_aws(local_file, bucket, s3_file):
    try:
        s3_client.upload_file(local_file, bucket, s3_file)
        print("Upload Successfully")
        return True
    except FileNotFoundError:
        print("The file was not found")
        return False
    except NoCredentialsError:
        print("Credentials not available")
        return False
#folder_name = match_response['FaceMatches'][0]['Face']['ExternalImageId']  #it's name of your folders
#uploaded = upload_to_aws(nowtime+'.jpg', bucket, folder_name +'/'+ nowtime+'.jpg')


# In[ ]:
    
#新增使用者
def add_new_user():
    while True:
        ID = input("\n請輸入學號(數字): ")
        name = input("請輸入英文名字: ")
        if ID.isnumeric() and name.isalpha(): #確認ID和Name是否只有字母和數字
            folder_name = ID + '_' + name #it's name of your folders
            s3_client.put_object(Bucket = bucket, Key=(folder_name+'/')) # 在s3上建立資料夾
            image_name, now = camera()
            uploaded = upload_to_aws(image_name, bucket, folder_name +'/'+ image_name)
            break
        else:
            print("學號只能有數字、名字中只能有英文字母，請重新輸入。")

#add_new_user()


# In[ ]:

#主選單
def menu():
    print("\n")
    print("簽到請輸入1")
    print("簽退請輸入2")
    print("個人資料建立請輸入3")
    print("退出程式請按任意其他按鍵")
    choice = input("請選擇功能: ")
    return choice


# In[ ]:


def main():
    while True:
        choice = menu()
        if choice == '1':
            sign('簽到')
        elif choice == '2':
            sign("簽退")
        elif choice == '3':
            add_new_user()
        else:
            break
    
main()


# In[ ]:




