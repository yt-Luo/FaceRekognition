#!/usr/bin/env python
# coding: utf-8

# In[ ]:


'''臉部辨識簽到退

功能: 比對本地照片與s3照片集合，確認是否有此人存在，並紀錄簽到退時間

前置作業:
在S3上開兩個bucket，指派一個用來index，一個用來留存data，並打開版本控制功能
確認member.json和course.json放在data資料夾中，且data資料夾與程式碼存放路徑一致
準備AWS educate的access key
管理員應有成員和課程編號資料可以看


條件限制:
1.若S3 folder name中有中文或符號會導致index_face()出現error
2.如果新增到s3的照片沒有人臉，有IndexError

Future Work: @author: ytLuo 2020.12.21
簽到退後計算已出席時數和剩餘時數  -->用時間戳計算跟課程時間的差距，推算狀態為遲到、早退或準時，透過狀態推算本次上課時數，再與前面加總
程式碼在網頁跑 --> 用執行檔?

Future Work finished:
v2.
 由本地新增使用者而不是s3 --> add_new_user()
 加入簽退功能 --> sign(state)
 上傳後刪除本地資料 --> delete_folder()
v3.0.0 
 Similarity和Confidence到小數點第二位 -->格式改%.2f%%
 每次拍照都留存，但是比對只用一張照片  -->拆兩個bucket，一個index，一個放data
 只在資料修改時重建集合，不要每次都建立集合，不然index太久
 退訓成員的資料留存，但不加入集合比對。更新status:dropout --> delete_member()
 只有管理員可以刪除成員資料 -->加入管理者模式 admin()
 照片上記錄時間，人臉的圖片檔加上文字 --> add_watermark()
 辨識完成加語音回覆，「2020年12月17日08點30分10號廖俊傑已簽到！祝你有個美好的一天！」 -->say()
v3.1.0
 學號姓名時間存資料庫 -->載入課程和人員檔案到，用list和dict比對與紀錄資料
'''


# In[ ]:


#pip install boto3
#pip install opencv-python
#pip install pyttsx3


# In[ ]:


import boto3
import cv2
import os
import shutil
import pyttsx3
import time
import json


# In[ ]:


# 注意session time是否逾時
def AWS_access():
    global ACCESS_KEY, SECRET_KEY, SESSION_TOKEN
    ACCESS_KEY = input("AWS access key: ")
    SECRET_KEY = input("AWS secret key: ")
    SESSION_TOKEN = input("AWS session token: ")
    return ACCESS_KEY, SECRET_KEY, SESSION_TOKEN
    
ACCESS_KEY = 'ASIASVAWICX3JTFI3MOD'
SECRET_KEY = 'wMGA+91TuLa6DJ7wegizrCCq7O3iDLMcVBmZ7GNp'
SESSION_TOKEN = 'FwoGZXIvYXdzEPH//////////wEaDK4FXEz/Hc2GsBzQBiK1ATrWtq7TSXkRVQnkmLUrBWCXIkpVYnGmTfKOyJhselpNfXYMrem8TJOSyNuguBtheUMms+2lorXjQNo3YG2vD6RDk5+L9l35sgveCk/Lk+Dc5NeSHsqs/MjPzWvqhc8cF4JhqChOzbqbElTRbvHjHR2HW2VEBuNaC7RzhZlT+6UdhF4DKtXTsIkHGqR0xBJ8aO4JL3582w3QMSKXPinHQM2MGp4q8cwVqV/oYR79Rruop8QEd0oo8JyB/wUyLT1dcNL87GO9bmPvAHWk8SIdv6vS/jkuN1Fz7bAUO9WZX6BTyWbuLPP+8nGitQ=='


# In[ ]:


# 自訂
bucket_index = 'facialanalysisproject' #S3 bucket name 放index用的照片

bucket_data = 'rekognitiondata198' # S3 bucket name 放每次簽到退的照片

collectionId='rekognitionProject' #collection name


# In[ ]:


# 上傳檔案到s3的folder裡
from botocore.exceptions import NoCredentialsError
def upload_to_aws(local_file, bucket, s3_file):
    s3_client = boto3.client('s3',aws_access_key_id=ACCESS_KEY, 
                         aws_secret_access_key=SECRET_KEY, 
                         aws_session_token=SESSION_TOKEN) 
    try:
        s3_client.upload_file(local_file, bucket, s3_file)
        print("Upload successfully.")
        return True
    except FileNotFoundError:
        print("The file was not found.")
        return False
    except NoCredentialsError:
        print("Credentials not available.")
        return False
#folder_name = match_response['FaceMatches'][0]['Face']['ExternalImageId']  #it's name of your folders
#upload_to_aws(nowtime+'.jpg', bucket, folder_name +'/'+ nowtime+'.jpg')


# In[ ]:


# 輸入資料
def load_json(filename):
    with open("{}.json".format(filename), encoding = 'utf-8-sig') as file:
        data = json.load(file)
    return data

member = load_json('./data/member')
course = load_json('./data/course')


# In[ ]:


def output_json(dict, filename):
    with open("{}.json".format(filename), 'w', encoding='utf-8') as f:
        json.dump(dict, f)
#output_json(member, 'member')


# In[ ]:


#照相
def camera():
    global now_timestamp, now_struct
    if not os.path.isdir('./photo/'):
        os.makedirs('./photo/')
    print("開啟相機，請按q拍照")
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW) #開啟第一台相機  cv2.CAP_DSHOW可以解決一些版本問題
    while(True):
        ret, frame = cap.read() #捕獲一幀影象。ret代表成功與否（True 代表成功，False 代表失敗）。frame 就是攝影機的單張畫面
        cv2.imshow('frame', frame) # 顯示圖片
        if cv2.waitKey(1) & 0xFF == ord('q'):  # 按q拍照 #ord('q')如果按鍵為q，退出迴圈
            #waitKey(1) 中的數字代表等待按鍵輸入之前的無效時間，單位為毫秒，在這個時間段內按鍵 ‘q’ 不會被記錄，在這之後按鍵才會被記錄，並在下一次進入if語段時起作用。也即經過無效時間以後，檢測在上一次顯示影象的時間段內按鍵 ‘q’ 有沒有被按下，若無則跳出if語句段，捕獲並顯示下一幀影象。
            now_timestamp = time.time() # 取得目前時間戳記
            now_struct = time.localtime(now_timestamp)
            now_str = time.strftime("%Y-%m-%d_%H.%M.%S", now_struct) # 格式化時間
            image_name = now_str+'.jpg'
            cv2.imwrite('./photo/'+image_name, frame)  # 存檔，檔案名稱為拍照時間
            add_watermark('./photo/'+image_name, time.strftime("%Y-%m-%d %H:%M:%S", now_struct)) # 加時間浮水印到照片
            break
    cap.release() # 釋放攝影機
    cv2.destroyAllWindows() # 關閉所有 OpenCV 視窗
    return image_name
#camera()


# In[ ]:


#加時間浮水印到照片
from PIL import Image, ImageDraw, ImageFont
def add_watermark(img_file, watermark):
    # 建立繪畫物件
    image = Image.open(img_file)
    draw = ImageDraw.Draw(image)
    myfont = ImageFont.truetype('C:/windows/fonts/Arial.ttf',size=20)
    fillcolor = '#ff0000'   #RGB紅色 
    width,height = image.size
    # 引數一：位置（x軸，y軸）；引數二：填寫內容；引數三：字型；引數四：顏色
    draw.text((width - 200, height-35), watermark, font=myfont, fill=fillcolor)
    image.save(img_file)
#image_name = camera()
#add_watermark('./photo/'+image_name, now.strftime("%Y-%m-%d %H:%M:%S")) # 加時間浮水印到照片


# In[ ]:


#將s3上的照片指向要辨識的集合
def index_face(bucket = bucket_index):
    s3_client = boto3.client('s3',aws_access_key_id=ACCESS_KEY, 
                         aws_secret_access_key=SECRET_KEY, 
                         aws_session_token=SESSION_TOKEN)
    rek_client=boto3.client('rekognition', region_name='us-east-1', 
                        aws_access_key_id=ACCESS_KEY, 
                        aws_secret_access_key=SECRET_KEY,
                        aws_session_token=SESSION_TOKEN)
    # delete existing collection if it exists
    list_response=rek_client.list_collections(MaxResults=2)
    
    if collectionId in list_response['CollectionIds']:
        rek_client.delete_collection(CollectionId=collectionId)
    
    # create a new collection
    rek_client.create_collection(CollectionId=collectionId)
    
    # add all images in current bucket to the collections    
    all_objects = s3_client.list_objects(Bucket = bucket )   # 列出s3內的所有物件
    
    print('indexing......')
    for content in all_objects['Contents']:
        collection_name,collection_image = content['Key'].split('/')
        if collection_image:
            label = collection_name
            #print('indexing: ',label)
            image = content['Key']    
            index_response=rek_client.index_faces(CollectionId=collectionId,
                                Image={'S3Object':{'Bucket':bucket,'Name':image}},
                                ExternalImageId=label,
                                MaxFaces=1,  #
                                QualityFilter="AUTO",
                                DetectionAttributes=['ALL'])
        
#index_face()    


# In[ ]:


#state = 簽到 or 簽退
def sign(state):
    rek_client=boto3.client('rekognition', region_name='us-east-1', 
                        aws_access_key_id=ACCESS_KEY, 
                        aws_secret_access_key=SECRET_KEY,
                        aws_session_token=SESSION_TOKEN)
    image_name = camera()
    while True:      
        print('captured '+image_name)
        with open('./photo/'+image_name, 'rb') as image:
            try: #match the captured imges against the indexed faces
                match_response = rek_client.search_faces_by_image(CollectionId=collectionId, 
                                                                  Image={'Bytes': image.read()}, 
                                                                  MaxFaces=1, #要傳回的最大臉數
                                                                  FaceMatchThreshold=85) #傳回的臉孔 符合的最小信心度
                if match_response['FaceMatches']:
                    folder_name = match_response['FaceMatches'][0]['Face']['ExternalImageId']
                    id = int(folder_name)
                    name = member[id-1].get("name")
                    print('歡迎您來上課！' if state == '簽到' else '簽退成功，可以下課回家了~')
                    print(name, member[id-1].get('title'), '已'+state)
                    print('Similarity: %.2f%%'%(match_response['FaceMatches'][0]['Similarity']))
                    print('Confidence: %.2f%%'%(match_response['FaceMatches'][0]['Face']['Confidence']))
                    print('您的'+state+'時間為',  time.strftime("%Y年%m月%d日%H點%M分", now_struct))
                     # 說話
                    say("%s，編號%d號，%s %s，已%s！祝您有個美好的一天！"%(time.strftime("%Y年%m月%d日，%H點%M分", now_struct), id, name, member[id-1].get("title"), state))
                    upload_to_aws('./photo/'+image_name, bucket_data, folder_name +'/'+ image_name) #上傳照片到s3_data
                    s ='in' if state == '簽到' else 'out'
                    member[id-1]['course'][no_C-1]['sign_'+s+'_time'] = time.strftime("%Y-%m-%d %H:%M:%S", now_struct) #紀錄簽到退時間
                    member[id-1]['course'][no_C-1]['timestamp_'+s] = now_timestamp  #紀錄簽到退時間戳記
                    break
                else:
                    print('No face matched')
                    break
            except:
                print('No face detected')
                break

#sign('簽到')
#sign('簽退')


# In[ ]:


#新增使用者
def add_new_user():
    while True:
        folder_name = input("\n請輸入成員編號(數字)，離開請輸入q: ") #it's name of your folders
        if folder_name.isnumeric() and int(folder_name)<=len(member) and folder_name > '0':
            id = int(folder_name)             
            choice = input("編號%s: %s %s。請確認身分(y/n): "%(member[id-1].get("no."),member[id-1].get("name"), member[id-1].get("title")))
            if choice == 'y' and member[id-1]['status'] != 'dropout':
                image_name = camera()
                upload_to_aws('./photo/'+image_name, bucket_index, folder_name +'/'+ image_name)
                index_face()
                print("資料建立完成")
                break
            elif choice == 'y' and member[id-1]['status'] == 'dropout':
                print("此成員已退出課程。")
                continue
            elif choice == 'n':
                continue    
            else:
                break
        elif folder_name == 'q':
            break        
        else:
            print("請輸入0-%d的數字"%(len(member)))
            
#add_new_user()


# In[ ]:


def delete_member(bucket_name = bucket_index):
    while True:
        folder_name = input("\n請輸入退出成員編號，離開請輸入q: ")
        if folder_name.isnumeric() and int(folder_name)<=len(member) and folder_name > '0':
            id = int(folder_name)             
            choice = input("編號%s: %s %s。\n請確認是否刪除此成員資料(y/n): "%(member[id-1].get("no."),member[id-1].get("name"), member[id-1].get("title")))
            if choice == 'y':
                s3 = boto3.resource('s3',aws_access_key_id=ACCESS_KEY, 
                         aws_secret_access_key=SECRET_KEY, 
                         aws_session_token=SESSION_TOKEN)
                bucket1 = s3.Bucket(bucket_name)
                bucket1 .objects.filter(Prefix=folder_name+'/').delete()
                member[id-1]['status'] = 'dropout'
                index_face()
                print("成員資料已移除")
                break               
            elif choice == 'n':
                continue    
            else:
                break
        elif folder_name == 'q':
            break        
        else:
            print("請輸入0-%d的數字"%(len(member)))
                                
#delete_member()
#member


# In[ ]:


def add_member():
    while True:
        folder_name = input("\n請輸入欲連結成員編號，離開請輸入q: ")
        if folder_name.isnumeric() and int(folder_name)<=len(member) and folder_name > '0':
            id = int(folder_name)             
            choice = input("編號%s: %s %s。\n請確認是否連結此成員資料(y/n): "%(member[id-1].get("no."),member[id-1].get("name"), member[id-1].get("title")))
            if choice == 'y':
                member[id-1]['status'] = 'training'
                #index_face()
                print("成員資料已連結")
                break
            
            elif choice == 'n':
                continue    
            else:
                break
        elif folder_name == 'q':
            break        
        else:
            print("請輸入0-%d的數字"%(len(member)))
        
                                
#add_member()
#member


# In[ ]:


#刪除本地data資料夾
def delete_folder(path):
    try:
        shutil.rmtree(path)
    except OSError as e:
        print(e)
    else:
        print()


# In[ ]:


#利用pyttsx3將文字轉語音
def say(sentence):
    '''
    pyttsx通過初始化來獲取語音引擎。當我們第一次呼叫init操作的時候，
    會返回一個pyttsx的engine物件，再次呼叫的時候，如果存在engine物件例項，
    就會使用現有的，否則再重新建立一個
    '''
    # 初始化
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    # index為設定音色種類，有0, 1可選  選1的時候沒說中文
    engine.setProperty('voice', voices[0].id)
    # 語速控制
    engine.setProperty('rate', 140)
    # 說的內容
    engine.say(sentence)
    # 朗讀一次
    engine.runAndWait()
#say('2020年12月17日，08點30分，編號10號，廖俊傑，已簽到！祝您有個美好的一天！')


# In[ ]:


#管理者頁面
def admin():
    global no_C
    no_C = 1
    while True:
        print("\n歡迎進入管理者介面！")
        print("1.選擇課程編號")
        print("2.取消連結成員資料")
        print("3.重新連結成員資料")
        print("4.更新Access key")
        print("5.進入使用者介面")
        choice = input("請選擇功能: ")
        if choice == '1':
            class_no = input("\n課程編號: ")
            no_C = int(class_no)
            class_info(no_C)
        elif choice =='2':
            delete_member()
        elif choice == '3':
            add_member()
        elif choice == '4':
            ACCESS_KEY, SECRET_KEY, SESSION_TOKEN = AWS_access()
            print("Access key已更新")
                  
        else:
            break
#admin()


# In[ ]:


#主選單
def menu():
    print("1.簽到")
    print("2.簽退")
    print("3.個人資料建立")
    print("4.儲存本次簽到退記錄並退出程式")
    choice = input("請選擇功能: ")
    return choice


# In[ ]:


def get_week_day(timestamp):
    struct_time = time.localtime(int(timestamp))
    x = struct_time.tm_wday
    week_day_dict = {
        0 : '一',
        1 : '二',
        2 : '三',
        3 : '四',
        4 : '五',
        5 : '六',
        6 : '日',
    }
    return week_day_dict[x]
#timestamp = time.time()
#get_week_day(timestamp)


# In[ ]:


def class_info(n=0):
    print("課程名稱: %s"%(course[n-1]['class']))
    print("上課時間: %s(%s) %s至%s"%(course[n-1]['school_day'],get_week_day(course[n-1]['timestamp_class']), course[n-1]['class_time'],course[n-1]['break_time']))
    print("授課教師: %s"%(course[n-1]['instructor']))
#class_info(1)


# In[ ]:


def main():
    admin()
    while True:        
        print("\n本次課程資料如下:")
        class_info(no_C)
        choice = menu()
        if choice == '1':
            sign('簽到')
        elif choice == '2':
            sign("簽退")
        elif choice == '3':
            add_new_user()
        elif choice == 'admin':
            pw = input("\n請輸入管理員密碼: ")
            if pw == 'admin':
                admin()
            else:
                print("密碼錯誤...您沒有權限")
                continue
        else:
            output_json(member, 'data/member')
            upload_to_aws('./data/member.json', bucket_data, 'data/member.json')
            delete_folder('./photo/')
            input("存檔完畢，任意鍵離開...")
            break
    
main()

