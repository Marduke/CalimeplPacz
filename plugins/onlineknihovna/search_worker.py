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
    def __init__(self, queue, browser, timeout, log, devel, number, iden, xml, title):
        self.queue = queue
        self.browser = browser
        self.timeout = timeout
        self.log = Log("search worker %i"%number, log, True)
        self.devel = devel
        self.number = number
        self.ident = iden
        self.xml = xml
        self.title = title

    def create_query(self):
        '''
        create url for HTTP request
        '''
        from urllib import urlencode
        q = ''
        if self.title:
            q += ' '.join(self.get_title_tokens(self.title))

        if isinstance(q, unicode):
            q = q.encode('utf-8')
        if not q:
            return None
        return self.BASE_URL+'book/search/textSearch/' + self.number + '?' + urlencode({
            'text':q
        })

    def run(self):
        if self.xml is None:
            raw = None
            try:
                url = self.create_query()
                self.log.info('download page search %s'%url)
                raw = self.browser.open(url, timeout=self.timeout).read().strip()
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

    def parse(self):
#         XPath = partial(etree.XPath, namespaces=self.NAMESPACES)
#         entry = XPath('//x:table[@id="listCategory"]')
#
#         entries = entry(self.xml)
        entries = self.xml.xpath('//table[@id="listCategory"]//tr')
        tmp_entries = []
        for book_ref in entries[1:]:
            title = book_ref.xpath('.//a[starts-with(@href, "/book/") and not(starts-with(@href, "/book/search"))]')
            authors = book_ref.xpath('.//a[starts-with(@href, "/book/search/authors")]/text()')
            auths = [] #authors surnames
            for i in authors:
                auths.append(i.split(",")[0])
            add = (title[1].get("href"), title[1].text, auths)
            if title != self.ident:
                tmp_entries.append(add)


