#!/usr/bin/python

__license__   = 'GPL v3'
__copyright__ = '2014, MarDuke <marduke@centrum.cz>'
__docformat__ = 'restructuredtext en'

from pprint import pprint
import sys, re, json

if __name__ == '__main__':
    '''
    Testing results of plugin results

    each plugin must have several test cases
    long search
    short story
    simple book
    short story compilation
    serie
    redirect search
    edition
    world

    each must have specified all result outputs metadata in testcases.dat

    test-cases name {
        type: 'long_search1'
        title:'Vlk'
        authors: 'E. E Knight'
        serie: 'abc'
        serie_index: 1
        tags: 'americka literatura','sci-fi','vedeckofantasticke romany'
        publisher: 'Triton / Trifid'
        pubdate: '2008-01-01T00:00:00'
        comments: 'bla bla.'
        identifiers: 'isbn':'9788073871499', 'baila':'/kniha/129544996'
        covers: 'http://baila.net/img/ebda30c55c4ef20d'
    }
    '''
    if len(sys.argv) == 2:
        name = sys.argv[1]
    else:
        print('No argument. Exiting...')
        exit()


    config  = file("%s\\testcase.json"%name, "r")
    data = json.loads(config.read().decode("utf-8-sig"))

    pprint(data)
    config.close()
#     config = {}
#     tc = open("%s\\testcase.dat"%name, "r")
#     in_comment = False
#     in_block = False
#     for line in tc.readlines():
#         line = line[:-1].strip()
#         if in_block == False and (line.startswith('\t') or line.startswith(' ' * 4)):
#             print(line)
#         elif line.endswith('{'):
#             name = re.search(".* {", line)
#         elif line.endswith('{'):
#
#             in_block = False
#     tc.close()

#     init = open("%s\\test.txt"%name, "r")
#     for line in init.readlines():
#         s
#
#
#     init.close()

