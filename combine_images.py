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

def combine_images(img1 : Image.Image,img2 : Image.Image):
    img = img1.copy()
    img.alpha_composite(img2)
    return img

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("InputImagesBasePath", help="input path")
    parser.add_argument("InputImagesToAddPath", help="input path")
    parser.add_argument("OutputPath", nargs='?', default=".\\combine_results", help="output path")
    args = parser.parse_args()

    images_base = get_images(args.InputImagesBasePath)
    images_toadd = get_images(args.InputImagesToAddPath)

    if(images_base and images_toadd and args.OutputPath == parser.get_default("OutputPath") and not os.path.exists(parser.get_default("OutputPath"))):
        os.mkdir(parser.get_default("OutputPath"))

    taskbar = Taskbar(find_first_window(os.getpid()))
    progressbar = tqdm(bar_format="{desc}{percentage:3.0f}%|{bar:60}{r_bar}",colour='green',desc="Processed Images: ",mininterval=0)
    progressbar.reset(total=len(images_base) * len(images_toadd))

    for img_base_path in images_base:
        for img_toadd_path in images_toadd:
            fname1, fext1 = os.path.splitext(os.path.basename(img_base_path))
            fname2, fext2 = os.path.splitext(os.path.basename(img_toadd_path))
            output_filename = fname1 + fname2 + ".png"
            output_path = os.path.join(args.OutputPath,output_filename)
            img_base = Image.open(img_base_path)
            img_toadd = Image.open(img_toadd_path)
            newimg = combine_images(img_base,img_toadd)
            newimg.save(output_path, "PNG", optimize=False)
            progressbar.update(1)
            taskbar.setProgress(taskbar.hwnd,progressbar.n,progressbar.total)
    progressbar.close()
    taskbar.stop(taskbar.hwnd)
    taskbar.Flash(taskbar.hwnd)