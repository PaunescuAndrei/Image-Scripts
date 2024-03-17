import mimetypes
import cv2
import os
from threading import Thread
from threading import enumerate as tenumerate
import queue
from threading import Event
import signal
import time
from threading import Lock
from tqdm import *
import argparse
import re
from taskbarlib import Taskbar,find_first_window

stop = Event()
data_lock = Lock()
taskbar = Taskbar(find_first_window(os.getpid()))
progressBar = None

def atoi(text):
    return int(text) if text.isdigit() else text.lower()

def natural_keys(text):
    '''
    alist.sort(key=natural_keys) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    (See Toothy's implementation in the comments)
    '''
    return [ atoi(c) for c in re.split(r'(\d+)', text) ]

def handler(signum, frame):
	stop.set()

def flipImage(path):
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    img_flip_lr = cv2.flip(img, 1)
    # im_mirror.show()

    path_folder,filename_ext = os.path.split(path)
    filename,_ = os.path.splitext(filename_ext)

    newname = "{imagename}_flipped.png".format(imagename=filename)
    cv2.imwrite(os.path.join(path_folder,newname),img_flip_lr,  [cv2.IMWRITE_PNG_COMPRESSION, 6])

def flipImagesQueue(q):
    while(not q.empty() and not stop.is_set()):
        path = q.get()
        flipImage(path)
        with data_lock:
            progressBar.update(1)
        q.task_done()

def check_image(file):
    guess_type = mimetypes.guess_type(file)[0]
    if guess_type and (guess_type.startswith('image')):
        return True
    return False    

def main(path):
    global progressBar
    tqdm.write("Flipping Images:")
    totalFiles = 0
    start = time.time()

    proxyq = queue.Queue(maxsize=0)
    for root, dirs, files in os.walk(path):       
        for file in sorted(files,key=natural_keys):
            filepath = os.path.join(root, file)
            if(check_image(filepath)):
                proxyq.put(filepath)
                totalFiles += 1

    progressBar = tqdm(total=totalFiles,bar_format="{percentage:3.0f}%|{bar:60}{r_bar}")

    num_theads = 3
    workers = []
    for i in range(num_theads):
        # print('Starting thread ', i)
        worker = Thread(target=flipImagesQueue, args=(proxyq,),name="worker {}".format(i),daemon=True)
        workers.append(worker)
        worker.start()
		
    while (True):
        time.sleep(1)
        # print(proxyq.qsize())
        if(proxyq.empty() and len(tenumerate()) <= 3):
            progressBar.close()
            break
        if (stop.is_set()):
            progressBar.close()
            return False

    for worker in workers:
        worker.join()

    print('All tasks completed.')
    end = time.time()
    print(end - start)
    return True

# Driver Code 
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("FolderPath", help="Flip all images in this folder.")
    args = parser.parse_args()

    signal.signal(signal.SIGINT, handler)  
    mainthread = Thread(target = main,args=(args.FolderPath,))
    mainthread.start()
    while mainthread.is_alive():
        try:
            # for thread in tenumerate(): 
            # 	print(thread.name)
            if progressBar:
                taskbar.setProgress(taskbar.hwnd,progressBar.n,progressBar.total)
            mainthread.join(timeout = 0.1)
            # time.sleep(1)
        except IOError:
            pass #Gets thrown when we interrupt the join 
    taskbar.stop(taskbar.hwnd)
    taskbar.Flash(taskbar.hwnd)
