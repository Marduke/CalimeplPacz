#!/usr/bin/python

__license__   = 'GPL v3'
__copyright__ = '2014, MarDuke <marduke@centrum.cz>'
__docformat__ = 'restructuredtext en'

from zipfile import ZipFile
import os, sys, shutil

if __name__ == '__main__':
    if len(sys.argv) == 2:
        name = sys.argv[1]
    build_dir = "..\\build"

    if not os.path.exists(build_dir):
        os.makedirs(build_dir)

    zf = ZipFile('%s\\%s.zip'%(build_dir, name), 'w')
    for f in os.listdir("..\\tmp"):
        zf.write("..\\tmp\\%s"%f, f)
    zf.close()