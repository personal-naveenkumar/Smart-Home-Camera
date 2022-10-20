from asyncore import poll
from fileinput import filename
import json
import random
import boto3
from threading import Thread
ec2 = boto3.resource('ec2')
sqs = boto3.client('sqs', region_name="us-east-1")
ssm_client = boto3.client('ssm')
import time
import time, threading
import requests
from requests.adapters import Retry, HTTPAdapter
import base64

s = requests.Session()

retries = Retry(total=1,
                backoff_factor=0.5,
                status_forcelist=[404],
                method_whitelist=["POST"]
                )

s.mount('http://', HTTPAdapter(max_retries=retries))

total_count = 1
free_instances = []
busy_instances=[]
loading_instances = []
stopped_instances = []
ipmap = {}
def create_inst(count):
    global loading_instances
    global total_count
    instances = ec2.create_instances(
    ImageId='ami-0fd356edb44cc2291',
    MinCount=1,
    MaxCount=count,
    InstanceType='t2.micro',
    SecurityGroupIds=['sg-05022aa08f2b4e3a1'])
    for instance in instances:
        loading_instances.append(instance.id)
        total_count=total_count+1
        ec2.create_tags(Resources=[instance.id], Tags=[
            {
                'Key': 'Name',
                'Value': "app-instance-"+str(total_count),
            },
            {
                'Key': 'CreatedBy',
                'Value': "script",
            },
            {
                'Key':'Role',
                'Value':'worker'
            },
        ])


def stop_inst(id):
    print('stopping ' + str(id))
    ec2.instances.filter(InstanceIds = [id]).stop()
    loading_instances.append(id)

def poll_loading_inst():
    for instance in loading_instances:
        i = ec2.Instance(instance)
        if i.state['Name'] == 'running':
            # print('requesting..' + i.public_ip_address)
            try:
                r = s.get("http://"+i.public_ip_address+":8000/health")
                if r.status_code==200:
                    # print(i.public_ip_address)
                    free_instances.append(instance)
                    loading_instances.remove(instance)
                    ipmap[instance]=i.public_ip_address
            except requests.exceptions.ConnectionError:
                print('Checking Health..')
            # print('done..')
        elif i.state['Name'] == 'stopped':
            stopped_instances.append(instance)
            loading_instances.remove(instance)
    threading.Timer(2, poll_loading_inst).start()

def restart_inst(id):
    ec2.instances.filter(InstanceIds = [id]).start()
    loading_instances.append(id)

def find_inst():
    for instance in ec2.instances.all():
        if(instance.tags==None):
            continue
        for tag in instance.tags:
            if tag["Key"]=='Role' and tag["Value"]=="worker":
                if instance.state['Name']=='running':
                    r = s.get("http://"+instance.public_ip_address+":8000/health")
                    if r.status_code==200:
                        free_instances.append(instance.id)
                        ipmap[instance.id]=instance.public_ip_address
                    else:
                        stop_inst(instance.id)
                elif instance.state['Name']=='stopped':
                    stopped_instances.append(instance.id)
    print('free:' + str(len(free_instances)))
    print('stopped:'+ str(len(stopped_instances)))
# def startWs(instance):
#      cmd = ['cd ~','export FLASK_APP=face_recognition.py','flask run --host=0.0.0.0 --port=8000']
#      resp = ssm_client.send_command(
#         DocumentName="AWS-RunShellScript",
#         Parameters={'commands': cmd},
#         InstanceIds=[instance],
#     )

def sendSqs(filename, result):
    queue_url = 'https://sqs.us-east-1.amazonaws.com/600083409750/OutputQ.fifo'
    response = sqs.send_message(
    QueueUrl=queue_url,
    MessageGroupId='2',
    MessageDeduplicationId=(filename+str(random.randint(1,100))),
    MessageBody=json.dumps({
        'fileName':filename,
        'result':result
        })
    )
    # print(filename + str(response))

def recSqs():
    queue_url = 'https://sqs.us-east-1.amazonaws.com/600083409750/InputQ.fifo' 
    response = sqs.receive_message(
    QueueUrl=queue_url,
    MaxNumberOfMessages=1,
    VisibilityTimeout=200,
    WaitTimeSeconds=0
    )
    
    if('Messages' not in response):
        print('Checking Message')
    else:
        message = response['Messages'][0]
        receipt_handle = message['ReceiptHandle']

        msg = json.loads(message['Body'])
        img = msg['img']
        filename=msg['fileName']
        print('received '+filename)
        # sqs.delete_message(
        #     QueueUrl=queue_url,
        #     ReceiptHandle=receipt_handle
        # )
        instance = getfreeinst()
        ip = ipmap[instance]
        #call in different thread
        thread = Thread(target = sendreq, args = (instance,"http://"+ip+":8000/",img,filename,receipt_handle ))
        thread.start()
        # sendreq(instance,"http://"+ip+":8000/",img,filename)
    threading.Timer(0.5, recSqs).start()


def getfreeinst():
    global qlen
    res=0
    total_live = len(free_instances) + len(loading_instances) + len(busy_instances)
    if total_live==0:
        time.sleep(5)
        queue_url = 'https://sqs.us-east-1.amazonaws.com/600083409750/InputQ.fifo'
        n = sqs.get_queue_attributes(QueueUrl=queue_url,AttributeNames=['ApproximateNumberOfMessages'])['Attributes']['ApproximateNumberOfMessages']
        n=int(n)
        res=min(20,n)
    else:
        res=qlen
    if len(free_instances)==0:
        total = len(free_instances) + len(loading_instances) + len(busy_instances) + len(stopped_instances)
        if(len(stopped_instances)!=0):
            for inst in stopped_instances:
                restart_inst(inst)
                res=res-1
                if res<=0:
                    break;
        if res>0:
            res=min(res,20-total)
        if res>0:
            create_inst(res)
    while(len(free_instances)==0):
        time.sleep(1)
    instance = free_instances.pop(0)
    busy_instances.append(instance)
    # print('free:' + str(len(free_instances)))
    # print('busy:' + str(busy_instances))
    print('qlen:' + str(qlen))
    return instance

def sendreq(instance,url,img,filename,receipt_handle):
    print('sending req '+filename)
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    payload = json.dumps({"image": img, "filename": filename})
    response = requests.post(url, data=payload, headers=headers)
    queue_url = 'https://sqs.us-east-1.amazonaws.com/600083409750/InputQ.fifo' 
    try:
        data = response.json()
        sendSqs(filename,data)
        # Delete received message from queue
        sqs.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=receipt_handle
        )
        print('completed ' + filename)              
    except requests.exceptions.RequestException:
        print(response.text)
    busy_instances.remove(instance)
    free_instances.append(instance)
qlen = 0
def pollqlen():
    global qlen
    queue_url = 'https://sqs.us-east-1.amazonaws.com/60012309750/InputQ.fifo' # needs to be updated
    res = sqs.get_queue_attributes(QueueUrl=queue_url,AttributeNames=['ApproximateNumberOfMessages'])['Attributes']['ApproximateNumberOfMessages']
    res=int(res)
    qlen = res
    threading.Timer(0.5, pollqlen).start()
    
def scalein():
    # queue_url = 'https://sqs.us-east-1.amazonaws.com/600083409750/InputQ.fifo'
    # res = sqs.get_queue_attributes(QueueUrl=queue_url,AttributeNames=['ApproximateNumberOfMessages'])['Attributes']['ApproximateNumberOfMessages']
    # res=int(res)
    res = qlen
    if res==0:
        scalein_helper()
        # i=len(free_instances)
        # while i>0:
        #     instance=free_instances.pop(len(free_instances)-1)
        #     stop_inst(instance)
        #     loading_instances.append(instance)
        #     i=i-1
    threading.Timer(2, scalein).start()

def scalein_helper():
    for instance in ec2.instances.all():
        if(instance.tags==None):
            continue
        for tag in instance.tags:
            if tag["Key"]=='Role' and tag["Value"]=="worker":
                if instance.state['Name']=='running':
                    try:
                        free_instances.remove(instance.id)
                    except:
                        print('instance id already removed')
                    stop_inst(instance.id)
                    stopped_instances.append(instance.id)

if __name__ == '__main__':
    find_inst()
    poll_loading_inst()
    pollqlen()
    recSqs()
    scalein()