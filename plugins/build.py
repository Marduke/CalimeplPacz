#!/usr/bin/python

__license__   = 'GPL v3'
__copyright__ = '2014, MarDuke <marduke@centrum.cz>'
__docformat__ = 'restructuredtext en'

import sys, os, re, shutil

def copyfile(src_file, out_file):
    src = out = None
    try:
        src = open(src_file, "r")
        out = open(out_file, "w")

        for line in src.readlines():
            out.write(re.sub(".*#REPLACE ", "", line))
    except Exception as e:
        print e
    finally:
        if src is not None:
            src.close()
        if out is not None:
            out.close()

if __name__ == '__main__':
    name = None
    directory = None
    temp_directory = "..\\tmp"
    auto_copy = ["devel", "metadata_compare", "pre_filter_compare","log"]

    if len(sys.argv) == 2:
        directory = name = sys.argv[1]
    elif len(sys.argv) == 3:
        directory, name = sys.argv[1:3]
    else:
        exit()

    if os.path.exists(temp_directory):
        shutil.rmtree(temp_directory)

    os.makedirs(temp_directory)

    #empty file with plugin name
    open("%s\\plugin-import-name-%s.txt"%(temp_directory,name), "w").close()

    for tmp in auto_copy:
        copyfile("%s.py"%tmp, "%s\\%s.py"%(temp_directory, tmp))

    for f in os.listdir(directory):
        #only python files
        if re.match(".*\.py$", f) != None:
            copyfile("%s\\%s"%(directory, f), "%s\\%s"%(temp_directory, f))
