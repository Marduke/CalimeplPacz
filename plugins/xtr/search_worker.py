#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import, print_function)

__license__   = 'GPL v3'
__copyright__ = '2014, MarDuke <marduke@centrum.cz>'
__docformat__ = 'restructuredtext en'

from threading import Thread
from calibre import as_unicode
from log import Log #REPLACE from calibre_plugins.xtr.log import Log

#Single Thread to process one page of search page
class SearchWorker(Thread):
    def __init__(self, queue, plugin, timeout, log, number, ident, xml, title, authors):
        Thread.__init__(self)
        self.queue = queue
        self.plugin = plugin
        self.timeout = timeout
        self.log = Log("search worker %i"%number, log)
        self.number = number
        self.identif = ident
        self.xml = xml
        self.title = title
        self.authors = authors

    def run(self):
        if self.xml is None:
            try:
                query = self.plugin.create_query(self.title, self.authors, self.number)
                self.xml = self.plugin.download_parse(query, self.timeout)
            except Exception as e:
                return as_unicode(e)
        self.parse()

    def parse(self):
        entries = self.xml.xpath('//table[@class="list_table2"]//tr[td[count(a) =2]]/td[2]')
        for book_ref in entries[1:]:
            parts = book_ref.xpath('./a/div/text()[1]')
            url = book_ref.xpath('./a/@href')
            title = parts[0].strip()
            auths = [] #authors surnames
            for i in parts[1].split(';'):
                auths.append(i.strip().split(",")[0])
            if len(parts) > 0 and len(url) > 0:
                add = (url[0].split('=')[-1], title, auths)
                if self.identif is None or title != self.identif:
                    self.queue.put(add)
            else:
                self.log('Title not found')