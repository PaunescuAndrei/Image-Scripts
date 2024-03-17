import os
import argparse

def main(path):
    files = os.listdir(path)
    for f in files:
        if(os.path.isfile(os.path.join(path,f))):
            fname1, fext1 = os.path.splitext(f)
            fname2, fext2 = os.path.splitext(fname1)
            if(fext2 is not None):
                os.rename(os.path.join(path,f),os.path.join(path,fname2+fext1))

if __name__ == '__main__': 
    parser = argparse.ArgumentParser()
    parser.add_argument("FolderPath", help="Remove second extension for files in this folder.",default=".")
    args = parser.parse_args()
    path = os.path.abspath(args.FolderPath)
    if(os.path.isdir(path)):
        main(path) 