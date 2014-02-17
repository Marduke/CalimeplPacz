#!/usr/bin/python
# vim:fileencoding=UTF-8:

__license__   = 'GPL v3'
__copyright__ = '2014, MarDuke <marduke@centrum.cz>'
__docformat__ = 'restructuredtext en'

import os, sqlite3, re


def check(title, authors):
    '''
    Check nkp
    '''
    pass

def make_combo(tokens):
    pass

def check_combo(arr):
    pass
#     my db
#     cal db
#     nkp

if __name__ == '__main__':
    conn = sqlite3.connect('reco.db')

    conn.execute('''CREATE TABLE IF NOT EXISTS book
        (id INT PRIMARY KEY     NOT NULL,
        title    TEXT    NOT NULL,
        authors    INT     NOT NULL);''')
    conn.execute('''CREATE TABLE IF NOT EXISTS author
        (id INT PRIMARY KEY     NOT NULL,
        name    TEXT     NOT NULL);''')

    conn_cal = sqlite3.connect('\\data\\knihovna\\Calibre Library\\metadata.db')

#     cursor = conn.execute("SELECT * FROM sqlite_master WHERE type='table'")
#     for row in cursor:
#         print(row[1])
#
#     cursor = conn.execute("SELECT * FROM books")
#     for row in cursor:
#         print([row[1], row[6]])
#
#     conn.close()
    files = [".txt", ".docx", ".doc", ".rtf", ".epub", ".pdb", ".djvu", ".mobi"]

    dirs = []
#     dirs.append("E:\\data\\knihy na prenos\\ebook\\")
    dirs.append("e:\\data\\knihy na prenos\\ebook\\E-Knihy.mobi\\Asimov, Isaac\\")

    try:
        directory = dirs.pop()
        for f in os.listdir(directory):
            act = directory + f
            print(f)
            if os.path.isdir(act):
                dirs.append(act)
            else:
                pos = f.rfind(".")
                if not f[pos:] in files:
                    print("pripona ee")
                    continue
                name = f[:pos]
                tokens = re.findall(r"[\w',]+", name)
                combo = make_combo(tokens)
                result = check_combo(combo)
    except Exception as e:
        print(e)

    conn.close()
    conn_cal.close()