#!/usr/bin/python

__license__   = 'GPL v3'
__copyright__ = '2014, MarDuke <marduke@centrum.cz>'
__docformat__ = 'restructuredtext en'

import os

def addDir(stack, directory):
    for n in os.listdir(directory):
        stack.append(directory + n)


if __name__ == '__main__':
    directory = "E:\\private\\tr\\mdone\\"
    acceptable = ["txt"]
    stack = []
    addDir(stack, directory)

    while(len(stack) > 0):
        thi = stack.pop()
        print thi
        if os.path.isdir(thi):
            print "dir"
            addDir(stack, thi)
        else:
            print "file"

