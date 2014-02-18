#!/usr/bin/env python
# vim:fileencoding=UTF-8
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2014, MarDuke <marduke@centrum.cz>'
__docformat__ = 'restructuredtext en'

from collections import OrderedDict

#REQUIRE log

from calibre import as_unicode
from calibre.ebooks.metadata.sources.base import Source, Option
from log import Log #REPLACE from calibre_plugins.obalkyknih.log import Log
import re

class ObalkyKnih(Source):

    name = 'Obalkyknih'
    version = (1, 0, 0)
    author = u'MarDuke marduke@centrum.cz'

    description = _('Downloads cover from obalkyknih.cz')
    capabilities = frozenset(['cover'])
    can_get_multiple_covers = True

    def download_cover(self, log, result_queue, abort, title=None, authors=None, identifiers={}, timeout=30, get_best_cover=False):
        self.log = Log(self.name, log)
        if not identifiers.has_key('isbn'):
            return

        isbn = identifiers.get('isbn')
        isbn = re.sub("-", "", isbn).strip()
        url = "http://www.obalkyknih.cz/api/cover?isbn=%s&return=js_callback&callback=display_cover&callback_arg="%isbn
        br = self.browser
        try:
            self.log('download cover metadata page %s'%url)
            data = br.open(url, timeout=timeout).read().strip()
        except Exception as e:
            self.log.exception('Failed to make download : %s caused %s'%(url, e))
            return None

        if len(data) > 0:
            if data.startswith("display_cover("):
                url = re.search('cover_url:".*"', data).group()
                url = url[11:-1]
                self.log("Found cover:%s"%url)
                br = self.browser
                self.log('Downloading cover from:%s'%url)
                try:
                    cdata = br.open_novisit(url, timeout=timeout).read()
                    result_queue.put((self, cdata))
                except:
                    self.log.exception('Failed to download cover from:', url)
            else:
                result_queue.put((self, data))
        else:
            self.log('No cover data found')

        url = "http://www.sckn.cz/ceskeknihy/images/covers_Orig/%s.jpg"%isbn
        try:
            self.log('download cover %s'%url)
            data = br.open(url, timeout=timeout).read().strip()
        except Exception as e:
            self.log.exception('Failed to make download : %s caused %s'%(url, e))
            return None

        if data:
            result_queue.put((self, data))


def test():
    from Queue import Queue
    from threading import Event
    from calibre.utils.logging import default_log
    p = ObalkyKnih(None)
    rq = Queue()
#     p.download_cover(default_log, rq, Event(), title='The Heroes', authors=('Joe Abercrombie',), identifiers={'isbn':'8086481107'})
    p.download_cover(default_log, rq, Event(), title='The Heroes', authors=('Joe Abercrombie',), identifiers={'isbn':'978-80-7384-656-5 '})
    print ('Downloaded', rq.qsize(), 'covers')

if __name__ == '__main__':
    test()

