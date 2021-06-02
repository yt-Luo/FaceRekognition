# 臉部辨識簽到退系統v3.2.1

#### 功能說明
在課堂點名時，由管理員用AWS帳號登入，以供老師與學員簽到退使用。<br>
系統利用電腦相機拍照後，比對本地照片與AWS S3上存放之照片集合，進行臉部辨識以確認此人身分，並紀錄簽到退時間。<br>
實際demo[影片連結](https://youtu.be/vSzr-tRt5SQ)<br>
0:05 應用場景<br>
0:36 功能介紹<br>
0:41 管理者登入&資料下載<br>
1:02 選擇當天課程<br>
1:23 建立成員資料<br>
1:45 簽到<br>
2:16 簽退<br>
2:44 刪除退訓成員<br>
3:19 將成員加回<br>
3:36 上傳資料到AWS S3並刪除本地資料<br>
3:49 未來功能<br>

#### 前置作業
1.在AWS S3上開兩個bucket，指派一個用來index，一個用來留存data，並打開版本控制功能<br>
2.確認member.json和course.json放在data資料夾中，且data資料夾與程式碼存放路徑一致<br>
3.準備AWS educate的access key<br>
4.管理員應有成員和課程編號資料可以看<br>


#### 條件限制
1.若S3 folder name中有中文或符號會導致index_face()出現error<br>
2.如果新增到s3的照片沒有人臉，有IndexError
