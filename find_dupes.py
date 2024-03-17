import argparse
import os
from skimage.metrics import structural_similarity
import cv2
import re
from timeit import default_timer as timer

def image_resize(image, width = None, height = None, inter = cv2.INTER_AREA):
    dim = None
    (h, w) = image.shape[:2]
    if width is None and height is None:
        return image
    if width is None:
        r = height / float(h)
        dim = (int(w * r), height)
    else:
        r = width / float(w)
        dim = (width, int(h * r))
    resized = cv2.resize(image, dim, interpolation = inter)
    return resized

def atoi(text):
    return int(text) if text.isdigit() else text.lower()

def natural_keys(text):
    '''
    alist.sort(key=natural_keys) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    (See Toothy's implementation in the comments)
    '''
    return [ atoi(c) for c in re.split(r'(\d+)', text) ]


def find_dupes(path):
    images_path = []
    images = {}
    dupes = []

    start = timer()
    print("Loading Images")
    i = 0
    for root, dirs, files in os.walk(path):
        if "imgflipper" in dirs:
            dirs.remove("imgflipper")        
        for file in sorted(files,key=natural_keys):
            tmp_path = os.path.normpath(os.path.join(root, file))
            images_path.append(tmp_path)
            img = cv2.imread(tmp_path, cv2.IMREAD_UNCHANGED)
            images[tmp_path] = image_resize(img,width=32)
            i+=1
            print(i)
    end = timer()
    print("Loaded all images " ,end - start)

    start = timer()
    images_path.sort(key=natural_keys)
    images_copy = images_path.copy()
    i = 1
    for img in images_path:
        print(img,i,len(images_path))
        if(img not in images_copy):
            i+=1
            continue
        current_dupes = set()
        img_path = img
        for img2 in images_copy.copy():
            if img2 == img:
                continue
            if(images[img_path].shape != images[img2].shape):
                continue
            score, diff = structural_similarity(images[img_path], images[img2], channel_axis=-1, full=True)
            if score > 0.999999: 
                current_dupes.add(img_path)
                current_dupes.add(img2)
                print("dupe ",score,img2)
                images_copy.remove(img2)
        if current_dupes:
            dupes.append(current_dupes)
            images_copy.remove(img)
        i+=1
    end = timer()
    print("Checking dupes " ,end - start)

    start = timer()
    count = 0
    for dupe in dupes:
        print(dupe)
        dupe_list = sorted(list(dupe),key=natural_keys)
        for item in dupe_list:
            path_folder,filename_ext = os.path.split(item)
            os.renames(item,os.path.join(path,"dupes",str(count),filename_ext))
        count+=1
    end = timer()
    print("Moving " ,end - start)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("FolderPath", default=".", nargs='?')
    args = parser.parse_args()
    find_dupes(os.path.abspath(os.path.normpath(args.FolderPath)))