import os
import shutil

person = "naveen_kumar"

all_frames = "./frames_and_videos/frames/"+person
train_path = "./data/real_images/train/"+person+"/"
val_path = "./data/real_images/val/"+person

#get list of all photos from frames_and_videos/frames/person
video_files = os.listdir(all_frames)

count = 0

for file in video_files:
    #for each image check if it present in real_images/train/person
    train_img_path = str(train_path+str(file))
    if not os.path.exists(train_img_path):
        
        #if no - then copy it to real_images/val/person
        img_src_path =  all_frames+"/"+str(file)
        shutil.copy(img_src_path, val_path)

        count += 1
        #we need test images of 50 (20% of train dataset)
        if count==50:
            break

print(person+" : Total files copied to val folder : "+str(count))