import os
import re
import argparse
import shutil

def atoi(text):
    return int(text) if text.isdigit() else text.lower()

def natural_keys(text):
    '''
    alist.sort(key=natural_keys) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    (See Toothy's implementation in the comments)
    '''
    return [ atoi(c) for c in re.split(r'(\d+)', text) ]

def listdir_filtered(path):
    files = os.listdir(path)
    if("desktop.ini" in files):
        files.remove("desktop.ini")
    if("Thumbs.db" in files):
        files.remove("Thumbs.db")
    return files

def shutil_copy(old, new):
    head, tail = os.path.split(new)
    if head and tail and not os.path.exists(head):
        os.makedirs(head)
    shutil.copy2(old, new)

def shutil_move(old, new):
    head, tail = os.path.split(new)
    if head and tail and not os.path.exists(head):
        os.makedirs(head)
    shutil.move(old, new)
    head, tail = os.path.split(old)
    if head and tail:
        try:
            os.removedirs(head)
        except OSError:
            pass

def mod_size(i):
    return len("%i" % i) # Uses string modulo instead of str(i)

def main(path,destinationpath,reverse,copy,pad):
    if(args.StartNumber == -1):
        maxnr = 0
        files = os.listdir(destinationpath)
        for f in sorted(files,key=natural_keys):
            if(os.path.isfile(os.path.join(destinationpath,f))):
                if(f == "desktop.ini"):
                    continue
                if("flipped" in f):
                    continue
                fname, fext = os.path.splitext(f)
                if(int(fname) > maxnr):
                    maxnr = int(fname)
        maxnr += 1
    else:
        maxnr = args.StartNumber

    ff = []

    for root, dirs, files in os.walk(path):
        if("info.txt" in files):
            files.remove("info.txt")
        if("desktop.ini" in files):
            files.remove("desktop.ini")
        if("Thumbs.db" in files):
            files.remove("Thumbs.db")
        for i in files:
            ff.append(os.path.join(root,i))

    max_number = len(ff) + maxnr
    digits = mod_size(max_number) if pad else 0

    for f in sorted(ff,key=natural_keys,reverse=reverse):
        filename = os.path.basename(f)
        fname, fext = os.path.splitext(filename)
        print(filename)
        newpath = os.path.join(path,"tmp",str(maxnr).rjust(digits,"0")+fext)
        if(copy):
            shutil_copy(f,newpath)
        else:
            shutil_move(f,newpath)
        maxnr += 1
    if(maxnr != args.StartNumber):
        print(maxnr - 1)
    
    for f in listdir_filtered(os.path.join(path,"tmp")):
        shutil_move(os.path.join(path,"tmp",f),os.path.join(destinationpath,f))

if __name__ == '__main__': 
    parser = argparse.ArgumentParser()
    parser.add_argument("StartNumber", type=int ,default=1, help="Starting number.")
    parser.add_argument("FolderPath", help="Source folder.")
    parser.add_argument("DestinationPath",nargs='?', default=None, help="Destination folder.")
    parser.add_argument("-r",'--reverse', action='store_true', help="Reverse order.")
    parser.add_argument("-c",'--copy', action='store_true', help="Copy instead of move.")
    parser.add_argument("-p",'--pad', action='store_true', help="Pad with zero in front.")
    args = parser.parse_args()
    path = os.path.abspath(args.FolderPath)
    destinationpath = args.DestinationPath
    if(os.path.isdir(path)):
        if(destinationpath == None):
            destinationpath = path
        main(path,destinationpath,args.reverse,args.copy,args.pad) 