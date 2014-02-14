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
from log import Log #REPLACE from calibre_plugins.baila.log import Log
import re

#Single Thread to process one page of search page
class SearchWorker(Thread):
    def __init__(self, queue, plugin, timeout, log, number, ident, xml, title):
        Thread.__init__(self)
        self.queue = queue
        self.plugin = plugin
        self.timeout = timeout
        self.log = Log("search worker %i"%number, log)
        self.number = number
        self.identif = ident
        self.xml = xml
        self.title = title

    def run(self):
        if self.xml is None:
            raw = None
            url = None
            try:
                url = self.plugin.create_query(self.title, self.number)
                self.log('download page search %s'%url)
                raw = self.plugin.browser.open(url, timeout=self.timeout).read().strip()
            except Exception as e:
                self.log.exception('Failed to make identify query: %r'%url)
                return as_unicode(e)

            if raw is not None:
                try:
                    parser = etree.XMLParser(recover=True)
                    clean = clean_ascii_chars(raw)
                    clean = re.sub("<br>", "<br/>", clean)
                    clean = re.sub("&nbsp;", " ", clean)
                    clean = re.sub("&hellip;", "...", clean)
                    self.xml = fromstring(clean, parser=parser)
                    if len(parser.error_log) > 0: #some errors while parsing
                        self.log('while parsing page occus some errors:')
                        self.log(parser.error_log)

                except Exception as e:
                    self.log.exception('Failed to parse xml for url: %s'%url)

        self.parse()

    def parse(self):
        entries = self.xml.xpath('//div[@class="works paging-container scrollable"]/div[@id]/div[@class="book-info"]')
        for book_ref in entries:
            title = book_ref.xpath('.//h3/a')
            authors = book_ref.xpath('.//span/a/text()')
            auths = [] #authors surnames
            for i in authors:
                auths.append(i.split(" ")[-1])

            if len(title) > 0:
                url = title[0].get("href")
                rindex = url.rfind('/')
                lindex = url.find('/', 1)
                url = url[lindex + 1:rindex]
                add = (url, title[0].text, auths)
                self.log(add)
                if self.identif is None or title != self.identif:
                    self.queue.put(add)
            else:
                self.log('title not found')


