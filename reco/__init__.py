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

def check_combo(tokens):
    combo = []
    print(tokens)
    for i in range(len(tokens)):
        print i
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

#     conn_cal = sqlite3.connect('\\data\\knihovna\\Calibre Library\\metadata.db')
    conn_cal = sqlite3.connect('\\knihovna\\Calibre Library\\metadata.db')

#     cursor = conn.execute("SELECT * FROM sqlite_master WHERE type='table'")
#     for row in cursor:
#         print(row[1])
#
#     cursor = conn.execute("SELECT * FROM books")
#     for row in cursor:
#         print([row[1], row[6]])
#
#     conn.close()
    files = [".txt", ".docx", ".doc", ".rtf", ".epub", ".pdb", ".djvu", ".mobi", ".pdf"]

    dirs = []
#     dirs.append("E:\\data\\knihy na prenos\\ebook\\")
#     dirs.append("e:\\data\\knihy na prenos\\ebook\\E-Knihy.mobi\\Asimov, Isaac\\")
#     dirs.append("\\books\\unsort\\")
    dirs.append("\\books\\unsort\\Khoury\\")
    try:
        directory = dirs.pop()
        for f in os.listdir(directory)[:1]:
            act = directory + f
            print(f)
            if os.path.isdir(act):
                dirs.append(act)
            else:
                pos = f.rfind(".")
                if not f[pos:] in files:
                    print("pripona ee " + f[pos:])
                    continue
                name = f[:pos]
                tokens = re.findall(r"[\w',]+", name)
                result = check_combo(tokens)
    except Exception as e:
        print(e)

    conn.close()
    conn_cal.close()