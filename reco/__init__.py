#!/usr/bin/python
# vim:fileencoding=UTF-8:

__license__   = 'GPL v3'
__copyright__ = '2014, MarDuke <marduke@centrum.cz>'
__docformat__ = 'restructuredtext en'

import os, sqlite3, re

def addDir(stack, directory):
    for n in os.listdir(directory):
        stack.append(directory + n)

def a(arr):
    print(arr)

if __name__ == '__main__':
    conn = sqlite3.connect('reco.db')

    conn.execute('''CREATE TABLE IF NOT EXISTS book
        (id INT PRIMARY KEY     NOT NULL,
        title    TEXT    NOT NULL,
        authors    INT     NOT NULL);''')
    conn.execute('''CREATE TABLE IF NOT EXISTS file
           (id INT PRIMARY KEY    NOT NULL,
           org_path    TEXT    NOT NULL,
           hash    INT    NOT NULL,
           id_book    INT);''')

#     conn = sqlite3.connect('\\data\\knihovna\\Calibre Library\\metadata.db')

#     cursor = conn.execute("SELECT * FROM sqlite_master WHERE type='table'")
#     for row in cursor:
#         print(row[1])
#
#     cursor = conn.execute("SELECT * FROM books")
#     for row in cursor:
#         print([row[1], row[6]])
#
#     conn.close()
    regexps = {
               "(.*)-(.*)\.txt":a
    }
    files = [".txt"]

#     directory = u"e:\\private\\tr\\mdone\\Knihy Sbírka (Fantasy Sci-Fi)\\Knihy\\I\\IRVING David\\"
    directory = u"e:\\private\\tr\\mdone\\Knihy Sbírka (Fantasy Sci-Fi)\\Knihy\\I\\IRVING David\\"
    for f in os.listdir(directory):
        if not f[-4:] in files:
            continue
        for reg in regexps.iteritems():
            print(f)
            print(reg)
            if re.match(reg[0], f):
                match = re.search(reg[0], f)
                reg[1](match.groups())

#     directory = "E:\\private\\tr\\mdone\\"
#     acceptable = ["txt"]
#     stack = []
#     addDir(stack, directory)
#
#     while(len(stack) > 0):
#         thi = stack.pop()
#         print thi
#         if os.path.isdir(thi):
#             print "dir"
#             addDir(stack, thi)
#         else:
#             print "file"
