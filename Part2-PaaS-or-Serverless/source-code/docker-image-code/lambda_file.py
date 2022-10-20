import torch
import torchvision
import torchvision.transforms as transforms
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models
from models.inception_resnet_v1 import InceptionResnetV1
from urllib.request import urlopen
from PIL import Image
import json
import numpy as np
# import argparse
import build_custom_model
import base64
import datetime
import io
import boto3
from boto3.dynamodb.conditions import Key

def lambda_handler(event, context):
    #print(event)
    labels_dir = "./checkpoint/labels.json"
    model_path = "./checkpoint/model_vggface2_best.pth"

    # read labels
    with open(labels_dir) as f:
        labels = json.load(f)
    print(f"labels: {labels}")

    # load the ML model
    device = torch.device('cpu')
    model = build_custom_model.build_model(len(labels)).to(device)
    model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu'))['model'])
    model.eval()
    print(f"Best accuracy of the loaded model: {torch.load(model_path, map_location=torch.device('cpu'))['best_acc']}")

    # load request image from trigger event
    encoded_image = json.loads(event['body'])['img']
    decoded_image_bytes = base64.b64decode(encoded_image.encode('utf-8'))
    img = Image.open(io.BytesIO(decoded_image_bytes))
    img_tensor = transforms.ToTensor()(img).unsqueeze_(0).to(device)

    # make prediction for request image
    outputs = model(img_tensor)
    _, predicted = torch.max(outputs.data, 1)
    result = labels[np.array(predicted.cpu())[0]]

    print(f'predicted image name:{result} at time:{datetime.datetime.now()}')
    
    # get information for this student from dynamoDB
    client = boto3.resource('dynamodb')
    table = client.Table('students_info')
    response = table.query(
        KeyConditionExpression=Key('name').eq(result)
    )
    response_items = response['Items']
    student_info = response_items[0]
    print(student_info)

    return {
        "isBase64Encoded": False,
        "statusCode": 200,
        "body": json.dumps({"name":student_info['name'], "major":student_info['major'], "year":student_info['year']}),
        "headers": {
            "content-type": "application/json"
        }
    }
