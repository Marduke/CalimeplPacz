#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import, print_function)

__license__   = 'GPL v3'
__copyright__ = '2014, MarDuke <marduke@centrum.cz>'
__docformat__ = 'restructuredtext en'

from threading import Thread
from calibre import as_unicode
from calibre.utils.cleantext import clean_ascii_chars
from calibre.ebooks.metadata.book.base import Metadata
from lxml import etree
from lxml.html import fromstring
from functools import partial
from log import Log #REPLACE from calibre_plugins.nkp.log import Log
import datetime, re, json

#Single Thread to process one page of searched list
class Worker(Thread):

    #string id
    ident = None

    #int id
    number = None

    def __init__(self, ident, result_queue, browser, log, relevance, plugin, xml, timeout=20):
        Thread.__init__(self)
        self.daemon = True
        self.ident, self.result_queue = ident, result_queue
        self.browser = browser.clone_browser()
        self.relevance = relevance
        self.plugin, self.timeout = plugin, timeout
        self.cover_url = self.isbn = None
        self.XPath = partial(etree.XPath, namespaces=plugin.NAMESPACES)
        self.xml = xml
        self.log = Log("worker %s"%self.ident, log)

    def run(self):
        if self.xml is not None:
            xml_detail = self.xml
        else:
            xml_detail = self.download_detail()

        if xml_detail is not None:
            try:
                result = self.parse(xml_detail)
                if result:
                    self.result_queue.put(result)
            except Exception as e:
                self.log.exception(e)
        else:
            self.log('Download metadata failed for: %r'%self.ident)

    def parse(self, xml_detail):
        xpath = self.XPath('//table[@id="record"]//tr')
        for row in xpath(xml_detail):
            ch = row.getchildren()
            if ch[0].text == 'Název':
                title, authors = self.parse_title_authors(ch[1])
            elif ch[0].text =='ISBN':
                isbn = self.parse_isbn(ch[1])
            elif ch[0].text == 'Nakl. údaje':
                publisher, pub_year = self.parse_publisher(ch[1])
            elif ch[0].text == 'Edice':
                serie, serie_index = self.parse_serie(ch[1])
            elif ch[0].text == 'Forma, žánr':
                tags = self.parse_tags(ch[1])

        if isbn is not None:
            cover = self.parse_cover(isbn)

        if title is not None and authors is not None:
            mi = Metadata(title, authors)
            mi.languages = {'ces'}
            mi.identifiers = {self.plugin.name:self.ident}
            mi.tags = tags
            mi.publisher = publisher
            mi.pubdate = pub_year
            mi.isbn = isbn
            mi.series = serie
            mi.series_index = serie_index
            mi.cover_url = cover

            if cover:
                self.plugin.cache_identifier_to_cover_url(self.ident, cover)

            return mi
        else:
            return None

    def parse_title_authors(self, data):
        tmp = data.xpath('.//text()')
        part = "".join(tmp).strip().split(';')[0].split('/')
        title = part[0]
        authors = []
        for s in part[1].split('a'):
            authors.append(s.strip())

        self.log('Found title:%s'%title)
        self.log('Found authors:%s'%authors)
        return [title, authors]

    def parse_rating(self, xml_detail):
        tmp = self.xpath_stars(xml_detail)
        if len(tmp) > 0:
            stars_ = int(tmp[0].replace(' %',''))
            rating = int(stars_ / 20)
            if stars_ % 20 > 0:
                rating += 1
            self.log('Found rating:%s'%rating)
            return rating
        else:
            self.log('Found rating:None')
            return None

    def parse_isbn(self, data):
        tmp = data.text
        isbn = tmp.split(' ')[0]
        self.log('Found ISBN:%s'%isbn)
        return isbn

    def parse_publisher(self, data):
        tmp = data.text
        part = tmp.split(':')[1].split(',')
        publisher = part[0].strip()
        pub_year = self.prepare_date(int(part[1].strip()))
        self.log('Found publisher:%s'%publisher)
        self.log('Found pub date:%s'%pub_year)
        return [publisher, pub_year]

    def parse_tags(self, data):
        parts = data.text.split('*')
        tags = []
        for p in parts:
            if len(p) > 0 :
                tags.append(p.strip())
        self.log('Found tags:%s'%tags)
        return tags

    def parse_serie(self, data):
        tmp = data.text
        parts = tmp.split(';')
        serie = parts[0].strip()
        serie_index = re.search("\d+", parts[1]).group()
        self.log('Found serie:%s[%s]'%(serie,serie_index))
        return [serie, serie_index]

    def parse_cover(self, isbn):
        isbn = re.sub("-", "", isbn)
        url = "http://www.obalkyknih.cz/api/cover?isbn=%s&return=js_callback&callback=display_cover&callback_arg="%isbn

        br = self.browser
        try:
            self.log('download page detail %s'%url)
            data = br.open(url, timeout=self.timeout).read().strip()
        except Exception as e:
            self.log.exception('Failed to make download : %r'%url)
            return None

        url = re.search('cover_url:".*"', data).group()
        url = url[11:-1]
        self.log("Found cover:%s"%url)
        return url

#         xml. xpath('//img/@src')
#         self.log(tmp)
#         if len(tmp) > 0:
#             self.log('Found covers:%s'%tmp[0])
#             return tmp[0]
#         else:
#             self.log('Found covers:None')
#             return None

    def download_detail(self):
        query = self.plugin.BASE_URL + self.ident
        br = self.browser
        try:
            self.log('download page detail %s'%query)
            data = br.open(query, timeout=self.timeout).read().strip()
            parser = etree.XMLParser(recover=True)
            clean = clean_ascii_chars(data)
            xml = fromstring(clean,  parser=parser)
            return xml
        except Exception as e:
            self.log.exception('Failed to make download : %r'%query)
            return None

    def prepare_date(self,year):
        from calibre.utils.date import utc_tz
        return datetime.datetime(year, 1, 1, tzinfo=utc_tz)

