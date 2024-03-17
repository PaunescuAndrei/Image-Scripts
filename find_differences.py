import os

tmp2_cropped = R"D:\wp\imgflipper\tmp2_cropped"
tmp = R"D:\wp\imgflipper\tmp"
tmp2_done =R"D:\wp\imgflipper\tmp2_done"

done = []
originals = []

def diff(list1, list2):
    return list(set(list1).symmetric_difference(set(list2)))  # or return list(set(list1) ^ set(list2))

def getFilesName(path):
    temp = []
    for i in os.listdir(path):
        fname, ext = os.path.splitext(i)
        temp.append(fname)
    return temp

done.extend(getFilesName(tmp))
done.extend(getFilesName(tmp2_cropped))
originals.extend(getFilesName(tmp2_done))

print(diff(done,originals))
print(len(done),len(originals))