import argparse
import os
import re

def atoi(text):
    return int(text) if text.isdigit() else text.lower()

def natural_keys(text):
    '''
    alist.sort(key=natural_keys) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    (See Toothy's implementation in the comments)
    '''
    return [ atoi(c) for c in re.split(r'(\d+)', text) ]

def getFiles(directory):
    inputs = []
    count = 0
    for root, dirs, files in os.walk(directory):
        for file in files:
            if(not "flipped" in file):
                count += 1
            inputs.append(os.path.join(root, file))
    return inputs,count

def getIndexByValue(vlist,value):
    try:
        b=vlist.index(value)
        return b
    except ValueError:
        return None

def main(args):
    wp_dir = R"D:\wp"
    files_new,count = getFiles(args.FolderPath)

    # check what files to keep and what to move
    rename_list = []
    keep_list = []
    for root, dirs, files in os.walk(wp_dir):
        if "imgflipper" in dirs:
            dirs.remove("imgflipper")
        for file in files:
            fname, fext = os.path.splitext(file)
            file_flipcheck = fname.rsplit("_",1)
            if(int(file_flipcheck[0]) >= args.Number):
                rename_list.append(os.path.join(root,file))
            else:
                keep_list.append(file)
    keep_list.sort(key=natural_keys)
    rename_list.sort(key=natural_keys)

    # rename old files
    old = [None]
    i = args.Number + count
    oldi = None
    rename_tmp_files = []
    for file in rename_list:
        dir,fnameext = os.path.split(file)
        fname, fext = os.path.splitext(fnameext)
        file_flipcheck = fname.rsplit("_",1)
        if(len(file_flipcheck) == 2 and file_flipcheck[1] == "flipped"):
            newname = f"{i}_flipped{fext}"
        else:
            newname = f"{i}{fext}"
        if(file_flipcheck[0] == old and len(file_flipcheck) == 2 and file_flipcheck[1] == "flipped"):
            newname = f"{oldi}_flipped{fext}"
            i -=1
        os.rename(file,os.path.join(dir,"tmp_"+newname))
        rename_tmp_files.append((os.path.join(dir,newname),os.path.join(dir,"tmp_"+newname)))
        old = file_flipcheck[0]
        oldi = i
        i += 1

    #move new files
    i = args.Number
    old = [None]
    oldi = None
    files_new.sort(key=natural_keys)
    for file in files_new:
        dir,fnameext = os.path.split(file)
        fname, fext = os.path.splitext(fnameext)
        file_flipcheck = fname.rsplit("_",1)
        if(len(file_flipcheck) == 2 and file_flipcheck[1] == "flipped"):
            newname = f"{i}_flipped{fext}"
        else:
            newname = f"{i}{fext}"
        if(file_flipcheck[0] == old and len(file_flipcheck) == 2 and file_flipcheck[1] == "flipped"):
            newname = f"{oldi}_flipped{fext}"
            i -=1
        os.rename(file,os.path.join(wp_dir,newname))
        old = file_flipcheck[0]
        oldi = i
        i += 1

    for item in rename_tmp_files:
        os.rename(item[1],item[0])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("Number", type=int , help="Insert at this number.")
    parser.add_argument("FolderPath", help="Folder to look for files.")
    args = parser.parse_args()
    main(args)
