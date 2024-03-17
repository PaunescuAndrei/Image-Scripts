import cv2
import os
import sys
from threading import Thread
from threading import enumerate as tenumerate
import queue
from threading import Event
import signal
import time
from threading import Lock
from tqdm import *
import argparse
import json
import win32console
from taskbarlib import Taskbar

stop = Event()
data_lock = Lock()
taskbar = Taskbar(win32console.GetConsoleWindow())
countAR = {}
filesAR = {}
progressBar = None

def calculate_aspect(width: int, height: int) -> str:
    temp = 0
    def gcd(a, b):
        """The GCD (greatest common divisor) is the highest number that evenly divides both width and height."""
        return a if b == 0 else gcd(b, a % b)
    if width == height:
        return "1:1"
    if width < height:
        temp = width
        width = height
        height = temp
    divisor = gcd(width, height)
    x = int(width / divisor) if not temp else int(height / divisor)
    y = int(height / divisor) if not temp else int(width / divisor)
    return f"{x}:{y}"

def getImageSizes(path):
    img = cv2.imread(path)
    return img.shape

def handler(signum, frame):
	stop.set()

def work(q):
    while(not q.empty() and not stop.isSet()):
        path = q.get()
        h,w,_ = getImageSizes(path)
        ar = calculate_aspect(w,h)
        with data_lock:
            countAR[ar] = countAR.get(ar,0) + 1
            if(ar != "16:9"):
                if ar in filesAR:
                    filesAR[ar].append(path)
                else:
                    filesAR[ar] = [path]
            progressBar.update(1)
        q.task_done()

def main(path,nt):
    global progressBar
    tqdm.write("Checking aspect ratios:")
    totalFiles = 0
    start = time.time()

    proxyq = queue.Queue(maxsize=0)
    for root, dirs, files in os.walk(path):
        if "imgflipper" in dirs:
            dirs.remove("imgflipper")        
        for file in files:
            proxyq.put(os.path.join(root, file))
            totalFiles += 1

    progressBar = tqdm(total=totalFiles,bar_format="{percentage:3.0f}%|{bar:60}{r_bar}")

    num_theads = nt
    workers = []
    for i in range(num_theads):
        # print('Starting thread ', i)
        worker = Thread(target=work, args=(proxyq,),name="worker {}".format(i),daemon=True)
        workers.append(worker)
        worker.start()
		
    while (True):
        time.sleep(1)
        # print(proxyq.qsize())
        if(proxyq.empty() and len(tenumerate()) <= 3):
            progressBar.close()
            break
        if (stop.isSet()):
            progressBar.close()
            return False

    for worker in workers:
        worker.join()
    for i in countAR:
        print(i,countAR[i])
    with open('result.json', 'w') as fp:
        json.dump(filesAR, fp, indent=4)
    print('All tasks completed.')
    end = time.time()
    print(end - start)
    return True

# Driver Code 
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("FolderPath", help="Folder to look for files.")
    parser.add_argument("-nt",help="Number of threads.",type=int,default=4)
    args = parser.parse_args()

    signal.signal(signal.SIGINT, handler)  
    mainthread = Thread(target = main,args=(args.FolderPath,args.nt))
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
