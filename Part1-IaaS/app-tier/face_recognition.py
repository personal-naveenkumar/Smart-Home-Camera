# importing libraries
import base64
import io
import json
from facenet_pytorch import MTCNN, InceptionResnetV1
import torch
from torchvision import datasets
from torch.utils.data import DataLoader
from PIL import Image
import csv
import os
import sys
from flask import Flask
from flask import jsonify
from flask import request

import boto3 
REGION = 'us-east-1' 
ACCESS_KEY_ID = 'dummy' 
SECRET_ACCESS_KEY = 'dummy'
INPUT_BUCKET = 'vperezb' 
KEY = ''
s3_resource = boto3.resource(
    's3', 
    region_name = REGION, 
    aws_access_key_id = ACCESS_KEY_ID,
    aws_secret_access_key = SECRET_ACCESS_KEY
) 
# s3_resource = boto3.client('s3', 
#     region_name = REGION, 
#     aws_access_key_id = ACCESS_KEY_ID,
#     aws_secret_access_key = SECRET_ACCESS_KEY)


# First run "set FLASK_APP=face_recognition.py" / "export" instead of set for linux;
# Run this with flask run --host=0.0.0.0 --port=8000


app = Flask(__name__)
@app.route("/health", methods=['GET'])
def check():
    return "pass"


def classify():
    f = request.files['file']
    test_image = f.filename
    f.save(test_image)
    # test_image = ".\\face_images_100\\test_01.jpg"
    result = face_match(test_image, 'data.pt')
    f.close()
    #print('Face matched with: ',result[0], 'With distance: ',result[1])
    if(len(result)!=0):
        updateS3(test_image, result[0]) 
        return result[0]
    return "FAILED"

@app.route("/", methods=['POST'])
def newclass():
    print('called new class')
    im_b64 = request.json['image']
    img_bytes = base64.b64decode(im_b64.encode('utf-8'))
    img = Image.open(io.BytesIO(img_bytes))
    result = face_match(img, 'data.pt')
    
    if(len(result)!=0):
        print(result[0])
        updateS3(img, result[0],request.json['filename'])
        response = app.response_class(
            response=json.dumps(result[0]),
            status=200,
            mimetype='application/json'
        )
        return response
    response = app.response_class(
        response=json.dumps("FAILED"),
        status=500,
        mimetype='application/json'
    )
    return response


def updateS3(img, result,filename):
    INPUT_BUCKET_NAME="cse546-bucket-input"
    OUTPUT_BUCKET_NAME = "cse546-bucket-output"
    img.save(filename)
    im = open(filename,'rb')
    # b = img.tobytes("xbm", "rgb")
    s3_resource.Bucket(INPUT_BUCKET_NAME).put_object(
        Key = filename, 
        Body = im
    )
    s3_resource.Bucket(OUTPUT_BUCKET_NAME).put_object(
        Key = str.split(filename,'.')[0], 
        Body = result
    )
    # s3_resource.upload_file(filepath, BUCKET_NAME, KEY)
    print("updated")

mtcnn = MTCNN(image_size=240, margin=0, min_face_size=20) # initializing mtcnn for face detection
resnet = InceptionResnetV1(pretrained='vggface2').eval() # initializing resnet for face img to embeding conversion

# test_image = sys.argv[1]
#dataset=datasets.ImageFolder('../data/test_images/') # photos folder path 
#dir_path = os.getcwd()
#dataset=datasets.ImageFolder(dir_path +'/face_images_100_1/') # photos folder path 
#idx_to_class = {i:c for c,i in dataset.class_to_idx.items()} # accessing names of peoples from folder names
#print(idx_to_class)

def collate_fn(x):
    return x[0]

#loader = DataLoader(dataset, collate_fn=collate_fn)

#face_list = [] # list of cropped faces from photos folder
#name_list = [] # list of names corrospoing to cropped photos
#embedding_list = [] # list of embeding matrix after conversion from cropped faces to embedding matrix using resnet
#
#for img, idx in loader:
#    face, prob = mtcnn(img, return_prob=True) 
#    if face is not None and prob>0.90: # if face detected and porbability > 90%
#        emb = resnet(face.unsqueeze(0)) # passing cropped face into resnet model to get embedding matrix
#        embedding_list.append(emb.detach()) # resulten embedding matrix is stored in a list
#        name_list.append(idx_to_class[idx]) # names are stored in a list
#
#
#data = [embedding_list, name_list]
#torch.save(data, 'data.pt') # saving data.pt file

def face_match(img, data_path): # img_path= location of photo, data_path= location of data.pt 
    # getting embedding matrix of the given img
    # img = Image.open(img_path)
    face, prob = mtcnn(img, return_prob=True) # returns cropped face and probability
    emb = resnet(face.unsqueeze(0)).detach() # detech is to make required gradient false
    
    saved_data = torch.load('data.pt') # loading data.pt file
    embedding_list = saved_data[0] # getting embedding data
    name_list = saved_data[1] # getting list of names
    dist_list = [] # list of matched distances, minimum distance is used to identify the person
    
    for idx, emb_db in enumerate(embedding_list):
        dist = torch.dist(emb, emb_db).item()
        dist_list.append(dist)
        
    idx_min = dist_list.index(min(dist_list))
    return (name_list[idx_min], min(dist_list))



