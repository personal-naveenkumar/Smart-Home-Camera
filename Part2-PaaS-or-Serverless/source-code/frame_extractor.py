import cv2
import os
from pathlib import Path

width = 160
height = 160
dim = (width, height)

def frameExtractor(path_to_video_files, path_to_frames):
    video_files = os.listdir(path_to_video_files)

    for file in video_files:
        try:
            if os.path.splitext(file)[1] !='.h264':
                continue
            print('******Extracting frames for video {}******'.format(file));
            video = cv2.VideoCapture(os.path.join(path_to_video_files, file))
            count = 0
            success = 1
            arr_img = []
            filenameprefix = str(format(file)[:-5])
            print('filenameprefix'+filenameprefix)
            
            # If such a directory doesn't exist, creates one and stores its Images
            if not os.path.isdir(os.path.join(path_to_frames, os.path.splitext(file)[0])):
                os.mkdir(os.path.join(path_to_frames, os.path.splitext(file)[0]))
            new_path = os.path.join(path_to_frames, os.path.splitext(file)[0])
            print("Saving to : "+new_path)

            print("reading frames...")
            while success:
                success, image = video.read()
                arr_img.append(image)
                count += 1
                
            count = 0
            print("processing frames...")
            for i in range(len(arr_img)-1):
                savedfile = str(filenameprefix+"_"+str(count)+".png")
                image_path = os.path.join(new_path,savedfile)
                cv2.imwrite(image_path, arr_img[i])
                #get original captured image
                image_original = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
                #crop image
                cropped_img = image_original[0:1080,420:1500]
                #resize image into dimensions 160x160
                resized_image = cv2.resize(cropped_img, dim, interpolation=cv2.INTER_LINEAR)
                #convert image to RGB
                image_rgb = cv2.cvtColor(resized_image, cv2.COLOR_RGBA2RGB)
                #save image
                cv2.imwrite(image_path, image_rgb)

                count += 1
                # if count>10:
                #     print("10 frames done. Stopping!")
                #     break
        except:
            continue

video_file_path = os.path.dirname(os.path.abspath(__file__))+"/videos"
frame_path = os.path.dirname(os.path.abspath(__file__))+"/frames"

def main():
    print("Running frame extractor...")
    frameExtractor(video_file_path,frame_path)


if __name__ == "__main__":
    main()