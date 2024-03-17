import hashlib
import mimetypes
from pathlib import Path
import os
from threading import Thread
import queue
from threading import Event
import signal
import time
from threading import Lock
import traceback
import argparse
import re
from taskbarlib import Taskbar,find_first_window
import keyboard
import subprocess
import shutil

#remove in python 3.11
mimetypes.add_type("image/webp", ".webp")

from rich.progress import Progress,Live,BarColumn,MofNCompleteColumn,TextColumn,TimeRemainingColumn,Task,ProgressColumn,TaskID
from rich.console import Group
from rich.panel import Panel
from rich.text import Text
from rich import print

class PercentageColumn(ProgressColumn):
    def __init__(self, table_column = None):
        super().__init__(table_column=table_column)

    def render(self, task: "Task") -> Text:
        if task.finished:
            style = "bar.finished"
        else:
            style = "bar.pulse"

        return Text(f"{task.percentage:>3.2f}%",style=style)

class StepsSpeedColumn(ProgressColumn):
    """Renders human readable transfer speed."""
    def render(self, task: "Task") -> Text:
        """Show data transfer speed."""
        speed = task.finished_speed or task.speed
        inv_speed = 1 / speed if speed else None
        rate = inv_speed if inv_speed and inv_speed > 1 else speed
        end_str = "s/it" if inv_speed and inv_speed > 1 else "it/s"
        if speed is None:
            return Text("?" + end_str, style="progress.data.speed")
        return Text(f"{rate:.2f}{end_str}", style="progress.data.speed")

class Console_GUI():
    live : Live = None
    current_directory : str | Text = ""
    old_size : str | Text = Text("0 Bytes",style="yellow2")
    new_size : str | Text = Text("0 Bytes",style="yellow2")
    saved_space : str | Text = Text.assemble(("0 Bytes (","yellow2"),("0%","bar.pulse"), (" Compression)","yellow2"))
    title : str | Text = ""
    progress : Progress = None
    time_started : float = None
    status: int = 1 # 0 = Paused, 1 = Running, 2 = Done, 3 = Exiting
    directories_task = None
    directories_task_id : TaskID = None
    files_task = None
    files_task_id : TaskID = None
    refresh_per_second = 1
    def __init__(self, title = "", refresh_per_second=1) -> None:
        self.title = title
        self.refresh_per_second = refresh_per_second
        self.progress = Progress(TextColumn("[progress.description]{task.description}"),
                            # TextColumn("[progress.percentage]{task.percentage:>3.2f}%"),
                            PercentageColumn(),
                            BarColumn(bar_width=None),
                            MofNCompleteColumn(),
                            # TimeElapsedColumn(),
                            # "<",
                            TimeRemainingColumn(compact=True,elapsed_when_finished=True),
                            StepsSpeedColumn(),
                            expand=True,refresh_per_second=self.refresh_per_second)
        self.directories_task_id = self.progress.add_task("[light_green]Dirs:", visible=False, total=100)
        self.files_task_id = self.progress.add_task("[light_green]Images:", total=100)
        self.directories_task = self.progress._tasks.get(self.directories_task_id,None)
        self.files_task = self.progress._tasks.get(self.files_task_id,None)
        self.time_started = time.time()
        self.live = Live(self.get_renderable(), refresh_per_second=self.refresh_per_second)

    def set_current_directory(self,directory):
        self.current_directory = directory

    def get_elapsed(self,task: Task = None,compact: bool = True, style : str = None):
        if task:
            time_elapsed = task.finished_time if task.finished else task.elapsed
        else:
            time_elapsed = time.time() - self.time_started
        style = style if style else "progress.elapsed"
        # Based on https://github.com/tqdm/tqdm/blob/master/tqdm/std.py
        minutes, seconds = divmod(int(time_elapsed), 60)
        hours, minutes = divmod(minutes, 60)
        if compact and not hours:
            formatted = f"{minutes:02d}:{seconds:02d}"
        else:
            formatted = f"{hours:d}:{minutes:02d}:{seconds:02d}"
        return Text(formatted, style=style)

    def get_renderable(self):
        title_text = Text(self.title,justify="center",style="yellow2")
        current_dir_text = Text.assemble(("Current Directory: ","light_green"), self.current_directory)
        old_size_text = Text.assemble(("Old Size: ","light_green"), self.old_size)
        new_size_text = Text.assemble(("New Size: ","light_green"), self.new_size)
        saved_space_text = Text.assemble(("Saved: ","light_green"), self.saved_space)
        group = Group(title_text,current_dir_text,self.progress,old_size_text,new_size_text,saved_space_text)
        elapsed = self.get_elapsed(style="yellow2")
        title = Text("Paused ") if self.status == 0 else Text("Running ") if self.status == 1 else Text("Done ") if self.status == 2 else Text("Exiting ") if self.status == 3 else ""
        title.stylize("yellow2")
        title.append_text(elapsed)
        border_style = "green" if (self.status == 1 or self.status == 2) else "yellow" if self.status == 0 else "red"
        return Panel(group,title=title, border_style=border_style, padding=(1, 1))
    def start(self):
        self.live.start(refresh=True)
    def stop(self):
        self.live.stop()

def formatSeconds(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f'{h:02d}:{m:02d}:{s:02d}'

def humanbytes(B):
    """Return the given bytes as a human friendly KB, MB, GB, or TB string."""
    negative = B < 0
    B = float(abs(B))
    KB = float(1024)
    MB = float(KB ** 2) # 1,048,576
    GB = float(KB ** 3) # 1,073,741,824
    TB = float(KB ** 4) # 1,099,511,627,776

    if B < KB:
        return f'{"-" if negative else ""}{B} Bytes'
    elif KB <= B < MB:
        return f'{"-" if negative else ""}{B / KB:.2f} KB'
    elif MB <= B < GB:
        return f'{"-" if negative else ""}{B / MB:.2f} MB'
    elif GB <= B < TB:
        return f'{"-" if negative else ""}{B / GB:.2f} GB'
    elif TB <= B:
        return f'{"-" if negative else ""}{B / TB:.2f} TB'

def atoi(text):
    return int(text) if text.isdigit() else text.lower()

def natural_keys(text):
    '''
    alist.sort(key=natural_keys) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    (See Toothy's implementation in the comments)
    '''
    return [ atoi(c) for c in re.split(r'(\d+)', text) ]

def subprocess_call(cmd):
    PIPE = -1
    STDOUT = -2
    DEVNULL = -3

    popen_params = {"stdout": DEVNULL,
                    "stderr": subprocess.PIPE,
                    "stdin": DEVNULL}

    if os.name == "nt":
        popen_params["creationflags"] = 0x08000000

    proc = subprocess.Popen(cmd, **popen_params)

    out, err = proc.communicate() # proc.wait()
    proc.stderr.close()
    if proc.returncode == 1:
        return False
    elif proc.returncode:
        print(proc.returncode)
        raise IOError(err.decode('utf8'))

    del proc
    return True

def pingocall(newpath,compressionlevel):
    """ convert image from path to newpath webp. """
    cmd = ["pingo","-lossless",f"-s{compressionlevel}", newpath]
    return subprocess_call(cmd)

def optimizeImage(old_path,tmppath,paths_dict,compressionlevel):
    tmpname = hashlib.md5(old_path.encode()).hexdigest()
    path = Path(old_path)
    # newpath = Path(fR"{path.parent}\tmp\{path.stem}.png")    
    tpath = Path(os.path.join(tmppath,f"{tmpname}.tmp{path.suffix}"))    
    newpath = Path(os.path.join(tmppath,f"{tmpname}{path.suffix}"))  
    if(newpath.exists()):
        paths_dict[old_path] = newpath
        return newpath;  
    newpath.parent.mkdir(exist_ok=True, parents=True)
    shutil.copy(path,tpath)
    result = pingocall(tpath,compressionlevel)
    if(result == False):
        print("Pingo stupid: ",path)
    shutil.move(tpath,newpath)
    paths_dict[old_path] = newpath
    return newpath

def handler(signum, frame):
    global gui
    stop.set()
    if gui is not None:
        gui.status = 3

def optimizeQueue(q,compressionlevel,paths_dict,tmppath):
    global oldsize,newsize,gui
    while(not q.empty() and not stop.is_set()):
        path = q.get()
        newpath = optimizeImage(path,tmppath,paths_dict,compressionlevel)
        with data_lock:
            try:
                oldsize += os.path.getsize(path)
                newsize += os.path.getsize(newpath)
                gui.saved_space = Text.assemble((f"{humanbytes(oldsize-newsize)} (","yellow2"),(f"{round((newsize/oldsize)*100,1)}%","bar.pulse"), (" Compression)","yellow2"))
                gui.old_size = Text(humanbytes(oldsize),style="yellow2")
                gui.new_size = Text(humanbytes(newsize),style="yellow2")
            except:
                print("Problem getting size for paths",path,newpath)
            gui.progress.update(gui.files_task_id,advance=1)
        q.task_done()
        if pause:
            while pause and not stop.is_set():
                Event().wait(timeout=1)

def optimize(basedir,images,compressionlevel,threadsnumber,globaltmp):
    global gui
    paths_dict = {}

    proxyq = queue.Queue(maxsize=0)

    for i in images:
        proxyq.put(i)

    if(globaltmp):
        # tmppath = os.path.join(os.path.abspath(os.getcwd()),"tmp_optimize")
        tmppath = globaltmp
    else:
        tmppath = os.path.join(basedir,"tmp_optimize")

    num_theads = threadsnumber
    workers = []
    for i in range(num_theads):
        worker = Thread(target=optimizeQueue, args=(proxyq,compressionlevel,paths_dict,tmppath),name="worker {}".format(i),daemon=True)
        workers.append(worker)
        worker.start()

    for worker in workers:
        worker.join()

    if (stop.is_set()):
        return False
    
    if os.path.isdir(tmppath):
        for file in images:
            if(os.path.exists(paths_dict[file])):
                os.remove(file)
                shutil.move(paths_dict[file], file)
            else:
                print(f"Couldn't find {file}")
        if(not globaltmp):
            shutil.rmtree(tmppath)
    return True

def check_image(file,nowebp):
    guess_type = mimetypes.guess_type(file)[0]
    # if guess_type and (guess_type.startswith('image/png') or guess_type.startswith('image/jpeg')):
    if guess_type and (guess_type.startswith('image/png') or guess_type.startswith('image/jpeg') or (guess_type.startswith('image/webp') and not nowebp)):
        return True
    return False    

def get_images(path,nowebp):
    images = []
    for root, dirs, files in os.walk(path):
        if 'tmp_optimize' in dirs:
            dirs.remove('tmp_optimize')        
        for file in sorted(files,key=natural_keys):
            filepath = os.path.join(root, file)
            if(check_image(filepath,nowebp)):
                images.append(filepath)
        break
    return images

def filter_files(files,nowebp):
    images = []
    for file in sorted(files,key=natural_keys):
        if(check_image(file,nowebp)):
            images.append(file)
    return images 

def main(files,dirs,compressionlevel,threadsnumber,globaltmp=False,nowebp=False):
    global gui

    if(len(dirs) == 1 and len(files) == 0):
        files = get_images(dirs[0],nowebp)
        dirs.clear()

    if(files):
        current_dir = os.path.dirname(files[0])
    elif(dirs):
        current_dir = os.path.dirname(dirs[0])
    else:
        current_dir = ""

    multiple = True if dirs else False

    gui.current_directory = Text(f"{os.path.basename(current_dir)}",style="yellow2")
    if(not multiple):
        gui.directories_task = None
        gui.progress.remove_task(gui.directories_task_id)
        gui.directories_task_id = None
    else:
        gui.progress.update(gui.directories_task_id,visible=True)

    total = 1
    if(dirs):
        if(files):
            total = 1 + len(dirs)
        else:
            total = len(dirs)
        gui.progress.reset(gui.directories_task_id,total=total)

    if(globaltmp):
        globaltmp = os.path.join(Path(__file__).parent.resolve(),"tmp_optimize")
        
    if(files):
        images = filter_files(files,nowebp)
        gui.progress.reset(gui.files_task_id, total=len(images))
        optimize(os.path.dirname(files[0]),images,compressionlevel,threadsnumber,globaltmp)
        if(total > 1):
            gui.progress.update(gui.directories_task_id,advance=1,refresh=True)
    if(dirs):
        for current_dir in dirs:
            gui.current_directory = Text(f"{os.path.basename(current_dir)}",style="yellow2")
            images = get_images(current_dir,nowebp)
            gui.progress.reset(gui.files_task_id, total=len(images))
            optimize(current_dir,images,compressionlevel,threadsnumber,globaltmp)
            gui.progress.update(gui.directories_task_id,advance=1,refresh=True)

def pingopy():
    global stop,data_lock,taskbar,gui,pause,oldsize,newsize
    parser = argparse.ArgumentParser()
    parser.add_argument("-gtmp",'--globaltmpfolder', action='store_true', help="create tmp folder in script location.")
    parser.add_argument("-nowebp",'--nowebp', action='store_true', help="ignore webp files.")
    parser.add_argument("-s", "--compressionlevel", type=int, default=4,choices=range(5), help="Compression level [0-4] [fastest-slowest]")
    parser.add_argument("-nt", "--threadsnumber", type=int, default=3, help="Number of threads.")
    parser.add_argument("Path", nargs='+', help="Optimize images using pingo.")
    parser.set_defaults(mode='encode')
    args = parser.parse_args()

    stop = Event()
    data_lock = Lock()
    taskbar = Taskbar(find_first_window(os.getpid()))
    gui = Console_GUI(title="Optimizing Images")
    pause = False
    oldsize = 0
    newsize = 0

    signal.signal(signal.SIGINT, handler)  
    signal.signal(signal.SIGBREAK, handler)  

    dirs = []
    files = []

    for file in args.Path:
        if(os.path.isdir(file)):
            dirs.append(file)
        if(os.path.isfile(file)):
            files.append(file)

    dirs.sort(key=natural_keys)
    files.sort(key=natural_keys)

    if(dirs):
        newdirs = []
        for d in dirs:
            tmpdirs = []
            for r, d, f in os.walk(d):
                if 'tmp_optimize' in d:
                    d.remove('tmp_optimize')        
                tmpdirs.append(r)
            newdirs += sorted(tmpdirs,key=natural_keys)
        dirs = newdirs
    
    mainthread = Thread(name="mainthread",target = main,args=(files,dirs,args.compressionlevel,args.threadsnumber,args.globaltmpfolder,args.nowebp))
    mainthread.start()
    gui.start()
    def toggle_pause():
        global pause,gui
        pause = not pause
        gui.status = 0 if pause else 1
        gui.live.update(gui.get_renderable())
    keyboard.add_hotkey('ctrl+alt+p', toggle_pause)
    while mainthread.is_alive():
        try:
            if dirs and gui.directories_task is not None and gui.directories_task.total:
                taskbar.setProgress(taskbar.hwnd,gui.directories_task.completed,gui.directories_task.total)
            elif gui.files_task is not None and gui.files_task.total:
                taskbar.setProgress(taskbar.hwnd,gui.files_task.completed,gui.files_task.total)
            mainthread.join(timeout = 0.5)
            gui.live.update(gui.get_renderable())
        except IOError:
            print(traceback.format_exc())
            pass 
    if(not stop.is_set()):
        gui.status = 2
        gui.live.update(gui.get_renderable())
    gui.stop()
    taskbar.stop(taskbar.hwnd)
    taskbar.Flash(taskbar.hwnd)

if __name__ == "__main__":
    pingopy()


