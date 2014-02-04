#!/usr/bin/python

__license__   = 'GPL v3'
__copyright__ = '2014, MarDuke <marduke@centrum.cz>'
__docformat__ = 'restructuredtext en'

import sys

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

    each must have specified all result outputs metadata by test-cases in test specification

    'test-cases':{
        'type': 'long_search1',
        'title':'Vlk',
        'authors': ['E. E Knight'],
        'serie': 'Země upírů',
        'serie_index': 1,
        'tags': ['americká literatura','sci-fi','vědeckofantastické romány'],
        'publisher': 'Triton / Trifid',
        'pubdate': '2008-01-01T00:00:00',
        'comments': 'Louisiana, druhá polovina 21. století: Země má nové šéfy Karany, mimozemšťany, kteří k nám pronikli mezihvězdnou bránou mezi světy. Už tady jednou byli, zůstaly po nich legendy o upírech a vlkodlacích. Tentokrát se na invazi důkladně připravili. Karané jsou staré nesmrtelné plémě, protože vysávají „vitální auru“ živých tvorů. Čím inteligentnější tvor, tím výživnější aura. Lidská aura je velice výživná. Karané rozvrátili lidskou společnost sérií globálních katastrof, upravili klima a nastolili Karské zřízení. Od lidí nechtějí mnoho – pouze jejich životy.',
        'identifiers': {'isbn':'9788073871499', 'baila':'/kniha/129544996'},
        'covers': ['http://baila.net/img/ebda30c55c4ef20d'],
    }
    '''
    if len(sys.argv) == 2:
        name = sys.argv[1]
    else:
        print('No argument. Exiting...')
        exit()

    init = open("%s\\__init__.py"%name, "r")

    init.close()

