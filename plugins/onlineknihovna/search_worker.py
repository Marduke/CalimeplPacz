#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import, print_function)

__license__   = 'GPL v3'
__copyright__ = '2014, MarDuke <marduke@centrum.cz>'
__docformat__ = 'restructuredtext en'

from threading import Thread
from calibre import as_unicode
from calibre.utils.cleantext import clean_ascii_chars
from lxml.html import fromstring
from lxml import etree
from log import Log #REPLACE from calibre_plugins.onlineknihovna.log import Log

#Single Thread to process one page of search page
class SearchWorker(Thread):
    def __init__(self, queue, plugin, timeout, log, devel, number, ident, xml, title):
        Thread.__init__(self)
        self.queue = queue
        self.plugin = plugin
        self.timeout = timeout
        self.log = Log("search worker %i"%number, log, False)
        self.devel = devel
        self.number = number
        self.identif = ident
        self.xml = xml
        self.title = title

    def run(self):
        if self.xml is None:
            raw = None
            url = None
            try:
                self.log.info([self.title, self.number])
                url = self.plugin.create_query(self.title, self.number)
                self.log.info('download page search %s'%url)
                raw = self.plugin.browser.open(url, timeout=self.timeout).read().strip()
            except Exception as e:
                self.log.exception('Failed to make identify query: %r'%url)
                return as_unicode(e)

            if raw is not None:
                try:
                    parser = etree.XMLParser(recover=True)
                    clean = clean_ascii_chars(raw)

                    self.devel.log_file('','search %s'%self.number, clean)

                    self.xml = fromstring(clean, parser=parser)
                except Exception as e:
                    self.log.exception('Failed to parse xml for url: %s'%self.url)

        self.parse()
        self.log.digg()

    def parse(self):
        entries = self.xml.xpath('//table[@id="listCategory"]//tr')
        for book_ref in entries[1:]:
            title = book_ref.xpath('.//a[starts-with(@href, "/book/") and not(starts-with(@href, "/book/search"))]')
            authors = book_ref.xpath('.//a[starts-with(@href, "/book/search/authors")]/text()')
            auths = [] #authors surnames
            for i in authors:
                auths.append(i.split(",")[0])
            add = (title[1].get("href"), title[1].text, auths)
            if self.identif is None or title != self.identif:
                self.queue.put(add)


