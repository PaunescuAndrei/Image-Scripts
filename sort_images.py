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
from PIL import Image
#remove in python 3.11
mimetypes.add_type("image/webp", ".webp")

from rich.progress import Progress,Live,BarColumn,MofNCompleteColumn,TextColumn,TimeRemainingColumn,Task,ProgressColumn,TaskID
from rich.console import Group,group
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
    resolutions : dict[str, int] = {}
    title : str | Text = ""
    progress : Progress = None
    time_started : float = None
    status: int = 1 # 0 = Paused, 1 = Running, 2 = Done, 3 = Exiting
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
        self.files_task_id = self.progress.add_task("[light_green]Images:", total=1)
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

    @group()
    def get_resolutions_group(self):
        for key,value in self.resolutions.items():
            yield Text.assemble((f"{key}: ","light_green"), str(value))

    def get_renderable(self):
        title_text = Text(self.title,justify="center",style="yellow2")
        current_dir_text = Text.assemble(("Current Directory: ","light_green"), self.current_directory)
        resolutions = self.get_resolutions_group()
        group = Group(title_text,current_dir_text,self.progress,resolutions)
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

def atoi(text):
    return int(text) if text.isdigit() else text.lower()

def natural_keys(text):
    '''
    alist.sort(key=natural_keys) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    (See Toothy's implementation in the comments)
    '''
    return [ atoi(c) for c in re.split(r'(\d+)', text) ]

def sortImage(old_path,newdir) -> str:
    path = Path(old_path)
    try:
        resolution = Image.open(old_path).size
    except IOError:
        print('Problem opening image: '+ str(old_path))
        return None

    resolution_str = f"{str(resolution[0])}x{str(resolution[1])}"
    newpath = Path(os.path.join(newdir,resolution_str,f"{path.name}"))
    if(newpath.exists()):
        if(newpath.samefile(old_path)):
            return resolution_str
        else:
            print('Image already exists: '+ str(newpath))
            return None
    newpath.parent.mkdir(exist_ok=True, parents=True)
    shutil.move(old_path,newpath)
    return resolution_str

def handler(signum, frame):
    global gui
    stop.set()
    if gui is not None:
        gui.status = 3

def sortQueue(q,newdir):
    global gui
    while(not q.empty() and not stop.is_set()):
        path = q.get()
        resolution = sortImage(path,newdir)
        with data_lock:
            old_value = gui.resolutions.get(resolution,0)
            gui.resolutions[resolution] = old_value + 1
            gui.progress.update(gui.files_task_id,advance=1)
        q.task_done()
        if pause:
            while pause and not stop.is_set():
                Event().wait(timeout=1)

def sort(newdir,images,threadsnumber):
    global gui

    proxyq = queue.Queue(maxsize=0)

    for i in images:
        proxyq.put(i)

    num_theads = threadsnumber
    workers = []
    for i in range(num_theads):
        worker = Thread(target=sortQueue, args=(proxyq,newdir),name="worker {}".format(i),daemon=True)
        workers.append(worker)
        worker.start()

    for worker in workers:
        worker.join()

    if (stop.is_set()):
        return False
    return True

def check_image(file):
    guess_type = mimetypes.guess_type(file)[0]
    # if guess_type and (guess_type.startswith('image/png') or guess_type.startswith('image/jpeg')):
    if guess_type and (guess_type.startswith('image/')):
        return True
    return False    

def get_images(path,recursive):
    images = []
    for root, dirs, files in os.walk(path):
        for file in sorted(files,key=natural_keys):
            filepath = os.path.join(root, file)
            if(check_image(filepath)):
                images.append(filepath)
        if(not recursive):
            break
    return images

def filter_files(files,nowebp):
    images = []
    for file in sorted(files,key=natural_keys):
        if(check_image(file,nowebp)):
            images.append(file)
    return images 

def main(dir, newdir, recursive, threadsnumber):
    global gui

    files = get_images(dir,recursive)

    if(files):
        current_dir = os.path.dirname(files[0])
    else:
        current_dir = ""

    gui.current_directory = Text(f"{os.path.basename(current_dir)}",style="yellow2")
    gui.live.refresh()

    if(files):
        gui.progress.reset(gui.files_task_id, total=len(files))
        sort(newdir,files,threadsnumber)

def sort_main():
    global stop,data_lock,taskbar,gui,pause
    parser = argparse.ArgumentParser()
    # multiple threads are slower for some reason
    parser.add_argument("-nt", "--threadsnumber", type=int, default=1, help="Number of threads.")
    parser.add_argument("-r",'--recursive', action='store_true', help="ignore webp files.")
    parser.add_argument("Path", nargs='?', default=".", help="Sort images in this folder.")
    parser.add_argument("TargetPath", nargs='?', default=None, help="Target location for sorted images.")
    args = parser.parse_args()

    stop = Event()
    data_lock = Lock()
    taskbar = Taskbar(find_first_window(os.getpid()))
    gui = Console_GUI(title="Sorting Images")
    pause = False

    signal.signal(signal.SIGINT, handler)  
    signal.signal(signal.SIGBREAK, handler)  

    path = os.path.abspath(args.Path)
    target_path = args.TargetPath if args.TargetPath else path
    if(not os.path.isdir(path)):
        print("Path is not a dir.")
        return

    mainthread = Thread(name="mainthread",target = main,args=(path, target_path, args.recursive, args.threadsnumber))
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
            if gui.files_task is not None and gui.files_task.total:
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
    sort_main()


