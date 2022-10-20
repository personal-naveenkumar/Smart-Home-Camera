import picamera
from time import sleep
from multiprocessing import Process
import boto3 
import threading
import base64
import json
import requests
import cv2
import time

REGION = 'us-east-1'
ACCESS_KEY_ID = 'bob' 
SECRET_ACCESS_KEY = 'alex'
s3_resource = boto3.resource(
    's3', 
    region_name = REGION, 
    aws_access_key_id = ACCESS_KEY_ID,
    aws_secret_access_key = SECRET_ACCESS_KEY
)
frame_sample=0.02
camera = picamera.PiCamera()
camera.resolution = (160,160)
camera.framerate=24
camera.raw_format='rgb'
def updateS3(filename):
    INPUT_BUCKET_NAME="proj2videos"
    vid = open(filename,'rb')
    s3_resource.Bucket(INPUT_BUCKET_NAME).put_object(
        Key = filename, 
        Body = vid
    )

def preProcess(image_path):
    width = 160
    height = 160
    dim = (width, height)
    image_original = cv2.imread(image_path+'.png', cv2.IMREAD_UNCHANGED)
    
    #change to resized_image if image is not 160x160
    image_rgb = cv2.cvtColor(image_original, cv2.COLOR_RGBA2RGB)
    #save image
    cv2.imwrite(image_path+'.png', image_rgb)

    
def requestPred(vid_path):
    sleep(1)
    try:
        threading.Thread(target=updateS3,args=(vid_path,)).start()
 
        vidcap = cv2.VideoCapture(vid_path)
        success,image = vidcap.read()
        if success:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)
            img_file = vid_path.split('.')[0] 
            cv2.imwrite(img_file+ '.png', image_rgb) 
            #preProcess(image_path)
            start_time = time.time()
            with open(img_file+ '.png', "rb") as f:
                im_bytes = f.read()        
            im_b64 = base64.b64encode(im_bytes).decode("utf8")
            imgdata=json.dumps({
                'img':im_b64,
            })
            
            url = 'https://3rocket4.execute-api.us-east-1.amazonaws.com/default/lambda_file'
            urlcont = 'https://irp5rocket.execute-api.us-east-1.amazonaws.com/default/test-8'

            r = requests.post(urlcont, data=imgdata)
            if r.status_code != 200:
                print(r)
            else:
                r = json.loads(r.text)
                print("The person " + str(img_file[4:])+" Recognized \""+ r['name'] +"\", \"" +r['major']+"\", \""+ r['year']+"\" " +"\n  Latency: {:.2f} seconds.".format(time.time() - start_time))
        else:
            print('failed for ' + vid_path)
    except:
        print('')
    

def capvid():
    camera.start_preview()
    start=time.time()
    for filename in camera.record_sequence(
            'clip%02d.h264' % (i+1) for i in range(duration*120)):
        #print('Recording to %s' % filename)
        if time.time()-start >= duration*60:
            break
        camera.wait_recording(0.5)
        threading.Thread(target=requestPred,args=(filename,)).start()
             

capvid()

