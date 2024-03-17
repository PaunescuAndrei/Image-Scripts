import argparse
from PIL import Image
import os
import mimetypes
from tqdm import tqdm
from taskbarlib import Taskbar,find_first_window

mimetypes.add_type("image/webp",".webp",strict=True)

def get_images(path):
    images = []
    for root, dirs, files in os.walk(path):
        if 'extend_results' in dirs:
            dirs.remove('extend_results')        
        for file in files:
            filepath = os.path.join(root, file)
            guess_type = mimetypes.guess_type(filepath)[0]
            if guess_type and guess_type.startswith('image'):
                images.append(filepath)
    return images

def add_margin(pil_img, top, right, bottom, left, color):
    width, height = pil_img.size
    new_width = width + right + left
    new_height = height + top + bottom
    result = Image.new(pil_img.mode, (new_width, new_height), color)
    result.paste(pil_img, (left, top))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("InputPath", help="input path")
    parser.add_argument("-t", "--top", type=int, default=0, help="top pad")
    parser.add_argument("-r", "--right", type=int, default=0, help="right pad")
    parser.add_argument("-b", "--bottom", type=int, default=0, help="bottom pad")
    parser.add_argument("-l", "--left", type=int, default=0, help="left pad")
    parser.add_argument("-c", "--color", type=tuple, default=(0,0,0,0), help="color")
    args = parser.parse_args()


    files = get_images(args.InputPath)

    if(files and not os.path.exists(os.path.join(args.InputPath,"extend_results"))):
        os.mkdir(os.path.join(args.InputPath,"extend_results"))

    taskbar = Taskbar(find_first_window(os.getpid()))
    progressbar = tqdm(bar_format="{desc}{percentage:3.0f}%|{bar:60}{r_bar}",colour='green',desc="Processed Images: ",mininterval=0)
    progressbar.reset(total=len(files))

    for img_path in files:
        basename = os.path.basename(img_path)
        fname, fext = os.path.splitext(basename)
        img = Image.open(img_path)
        newimg = add_margin(img,args.top,args.right,args.bottom,args.left,args.color)
        newimg.save(os.path.join(args.InputPath,"extend_results",f"{fname}.png"), "PNG", optimize=False)
        progressbar.update(1)
        taskbar.setProgress(taskbar.hwnd,progressbar.n,progressbar.total)
    progressbar.close()
    taskbar.stop(taskbar.hwnd)
    taskbar.Flash(taskbar.hwnd)