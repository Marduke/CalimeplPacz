#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import, print_function)

__license__   = 'GPL v3'
__copyright__ = '2014, MarDuke <marduke@centrum.cz>'
__docformat__ = 'restructuredtext en'

from threading import Thread
from calibre import as_unicode
from calibre.utils.cleantext import clean_ascii_chars
from calibre.utils.date import utc_tz
from calibre.ebooks.metadata.book.base import Metadata
from lxml import etree
from lxml.html import fromstring
from functools import partial
from log import Log #REPLACE from calibre_plugins.baila.log import Log
import datetime, re

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
        self.log = Log("worker %s"%ident, log)

    def initXPath(self):
        self.xpath_title = '//h1[@class="book-title t"]/text()'
        #TODO:
        self.xpath_authors = '//h2[@class="book-author t"]/span/a/text()'
        self.xpath_authors_coop = '//div[@class="book-contributors"]/text()'
        self.xpath_comments = '//div[@class="trunc-a"]/text()'
        self.xpath_stars = '//meta[@itemprop="ratingValue"]/@content'
        self.xpath_isbn = '//span[@itemprop="isbn"]/text()'
        self.xpath_publisher = '//span[@itemprop="publisher"]/text()'
        self.xpath_pubdate = '//span[@class="publish-year" and @itemprop="datePublished"]/text()'
        self.xpath_tags = '//div[@class="trunc-h"]//a[starts-with(@href, "/kategorie/")]/text()'
        #TODO:http://baila.net/kniha/129544996/vlk-zeme-upiru-1-kniha-e-e-knight
        self.xpath_serie = '//a[starts-with(@href, "/book/search/series%")]/text()'
        #TODO:
        self.xpath_serie_index = '//a[starts-with(@href, "/book/search/series_no%")]/text()'
        self.xpath_cover = '//div[@class="cover_with_links"]/div/img/@src'

    def run(self):
        self.initXPath()

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
            self.log.exception('Download metadata failed for: %s'%self.ident)

    def parse(self, xml_detail):
        title = self.parse_title(xml_detail)
        authors = self.parse_authors(xml_detail)
        comments = self.parse_comments(xml_detail)
        rating = self.parse_rating(xml_detail)
        isbn = self.parse_isbn(xml_detail)
        publisher = self.parse_publisher(xml_detail)
        pub_year = self.parse_pubdate(xml_detail)
        tags = self.parse_tags(xml_detail)
        serie, serie_index = self.parse_serie(xml_detail)
        cover = self.parse_cover(xml_detail)

        if title is not None and authors is not None:
            mi = Metadata(title, authors)
            mi.languages = {'ces'}
            mi.comments = as_unicode(comments)
            mi.identifiers = {self.plugin.name:self.ident}
            mi.rating = rating
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

    def parse_title(self, xml_detail):
        tmp = xml_detail.xpath(self.xpath_title)
        if len(tmp) > 0:
            self.log('Found title:%s'%tmp[0].strip())
            return tmp[0].strip()
        else:
            self.log('Found title:None')
            return None

    def parse_authors(self, xml_detail):
        tmp = xml_detail.xpath(self.xpath_authors)
        if len(tmp) > 0:
            auths = [tmp[0].strip()]
            coop = xml_detail.xpath(self.xpath_authors_coop)
            coop = re.sub("Další autoři:", "", coop[0])
            for name in coop.split(','):
                parts = name.split('(')
                if parts[1].startswith('autor'):
                    auths += [parts[0].strip()]

            self.log('Found authors:%s'%auths)
            return auths
        else:
            self.log('Found authors:None')
            return None

    def parse_comments(self, xml_detail):
        tmp = xml_detail.xpath(self.xpath_comments)
        if len(tmp) > 0:
            result = "".join(tmp).strip()
            self.log('Found comment:%s'%result)
            return result
        else:
            self.log('Found comment:None')
            return None

    def parse_rating(self, xml_detail):
        tmp = xml_detail.xpath(self.xpath_stars)
        if len(tmp) > 0:
            rating = float(tmp[0])
            self.log('Found rating:%s'%rating)
            return rating+1
        else:
            self.log('Found rating:None')
            return None

    def parse_isbn(self, xml_detail):
        tmp = xml_detail.xpath(self.xpath_isbn)
        if len(tmp) > 0:
            self.log('Found ISBN:%s'%tmp[0])
            return tmp[0]
        else:
            self.log('Found ISBN:None')
            return None

    def parse_publisher(self, xml_detail):
        tmp = xml_detail.xpath(self.xpath_publisher)
        if len(tmp) > 0:
            self.log('Found publisher:%s'%tmp[0])
            return tmp[0]
        else:
            self.log('Found publisher:None')
            return None

    def parse_pubdate(self, xml_detail):
        tmp = xml_detail.xpath(self.xpath_pubdate)
        if len(tmp) > 0:
            self.log('Found pubdate:%s'%tmp[0])
            return datetime.datetime(int(tmp[0]), 1, 1, tzinfo=utc_tz)
        else:
            self.log('Found pubdate:None')
            return (None, None)

    def parse_tags(self, xml_detail):
        tmp = xml_detail.xpath(self.xpath_tags)
        if len(tmp) > 0:
            self.log('Found tags:%s'%tmp)
            return tmp
        else:
            self.log('Found tags:None')
            return None

    def parse_serie(self, xml_detail):
        tmp = xml_detail.xpath(self.xpath_serie)
        if len(tmp) > 0:
            serie_name = tmp[0]
            serie_index = 0
            tmp2 = xml_detail.xpath(self.xpath_serie_index)
            if len(tmp2) > 0:
                serie_index = float(tmp2[0])

            self.log('Found serie:%s[%d]'%(serie_name, serie_index))
            return [serie_name, serie_index]

        else:
            self.log('Found serie:None')
            return [None, None]


        if len(tmp) == 0 or not tmp[0] == 'Série':
            self.log('Found serie:None')
            return [None, None]

        tmp = self.xpath_serie(xml_detail)
        if len(tmp) == 0:
            self.log('Found serie:None')
            return [None, None]
        else:
            index = 0
            if self.plugin.prefs['serie_index']:
                tmp_index = self.xpath_serie_index(xml_detail)
                if len(tmp_index) > 0:
                    for i, url in enumerate(tmp_index):
                        tmp_ident = int(url.split('-')[1])
                        if tmp_ident == self.number:
                            index = i + 1
                            break

            self.log('Found serie:%s[%i]'%(tmp[0],index))
            return [tmp[0], index]

    def parse_cover(self, xml_detail):
        tmp = xml_detail.xpath(self.xpath_cover)
        if len(tmp) > 0:
            self.log('Found covers:%s'%tmp[0])
            return tmp[0]
        else:
            self.log('Found covers:None')

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
