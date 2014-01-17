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
import datetime, inspect, re

#Single Thread to process one page of searched list
class Worker(Thread):

    #string id
    ident = None

    #int id
    number = None

    def __init__(self, ident, result_queue, browser, log, relevance, plugin, xml, devel, timeout=20):
        Thread.__init__(self)
        self.daemon = True
        self.ident, self.result_queue = ident, result_queue
        self.browser = browser.clone_browser()
        self.logger, self.relevance = log, relevance
        self.plugin, self.timeout = plugin, timeout
        self.cover_url = self.isbn = None
        self.devel = devel
        self.XPath = partial(etree.XPath, namespaces=plugin.NAMESPACES)
        self.xml = xml
        if xml is not None:
            self.number = int(ident)
        else:
            self.number = int(self.ident.split('-')[1])

    def initXPath(self):
        self.xpath_title = self.XPath('//x:span[@itemprop="name"]/text()')
        self.xpath_authors = self.XPath('//x:a[@itemprop="author"]/x:strong/text()')
        self.xpath_comments = self.XPath('//x:div[@id="annotation"]/text()')
        self.xpath_stars = self.XPath('//x:span[@id="book_rating_text"]/text()')
        self.xpath_isbn = self.XPath('//x:span[@itemprop="isbn"]/text()')
        self.xpath_publisher = self.XPath('//x:span[@itemprop="isbn"]/preceding-sibling::text()')
        self.xpath_tags = self.XPath('//x:td[@class="v_top"]/x:strong[2]/text()')
        self.xpath_serie_condition = self.XPath('//x:div[@id="right"]/x:fieldset[1]/x:legend/text()')
        self.xpath_serie = self.XPath('//x:div[@id="right"]/x:fieldset[1]/x:div/x:strong/text()')
        self.xpath_serie_index = self.XPath('//x:div[@id="right"]/x:fieldset[1]//x:div[@class="right_book"]/x:a/@href')
        self.xpath_cover = self.XPath('//x:td[@id="book_covers"]//x:img/@src')

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
                self.logexception(e)
        else:
            self.log('Download metadata failed for: %r'%self.ident)

    def parse(self, xml_detail):
        title = self.parse_title(xml_detail)
        authors = self.parse_authors(xml_detail)
        comments = self.parse_comments(xml_detail)
        rating = self.parse_rating(xml_detail)
        isbn = self.parse_isbn(xml_detail)
        publisher, pub_year = self.parse_publisher(xml_detail)
        tags = self.parse_tags(xml_detail)
        serie, serie_index = self.parse_serie(xml_detail)
        cover = self.parse_cover(xml_detail)

        if title is not None and authors is not None:
            mi = Metadata(title, authors)
            mi.languages = {'ces'}
            mi.comments = as_unicode(comments)
            mi.identifiers = {self.plugin.name:str(self.number)}
            mi.rating = rating
            mi.tags = tags
            mi.publisher = publisher
            mi.pubdate = pub_year
            mi.isbn = isbn
            mi.series = serie
            mi.series_index = serie_index
            mi.cover_url = cover

            if cover:
                self.plugin.cache_identifier_to_cover_url(str(self.number), cover)

            return mi
        else:
            return None

    def parse_title(self, xml_detail):
        tmp = self.xpath_title(xml_detail)
        if len(tmp) > 0:
            self.log('Found title:%s'%tmp[0])
            return tmp[0]
        else:
            self.log('Found title:None')
            return None

    def parse_authors(self, xml_detail):
        tmp = self.xpath_authors(xml_detail)
        if len(tmp) > 0:
            self.log('Found authors:%s'%tmp)
            return tmp
        else:
            self.log('Found authors:None')
            return None

    def parse_comments(self, xml_detail):
        tmp = self.xpath_comments(xml_detail)

        if len(tmp) > 0:
            result = "".join(tmp).strip()
            self.log('Found comment:%s'%result)
            return result
        else:
            self.log('Found comment:None')
            return None

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

    def parse_isbn(self, xml_detail):
        tmp = self.xpath_isbn(xml_detail)
        if len(tmp) > 0:
            self.log('Found ISBN:%s'%tmp[0])
            return tmp[0]
        else:
            self.log('Found ISBN:None')
            return None

    def parse_publisher(self, xml_more_info):
        tmp = self.xpath_publisher(xml_more_info)
        if len(tmp) > 0:
            data = tmp[-2].strip().split(' - ')
            if len(data) == 2:
                self.log('Found publisher:%s'%data[0])
                self.log('Found pub date:%s'%data[1])
                data[1] = self.prepare_date(int(data[1]))
                return data

        self.log('Found publisher:None')
        self.log('Found pub date:None')
        return (None, None)

    def parse_tags(self, xml_detail):
        tmp = self.xpath_tags(xml_detail)
        if len(tmp) > 0:
            result = tmp[0].split(' / ')
            self.log('Found tags:%s'%result)
            return result
        else:
            self.log('Found tags:None')
            return None

    def parse_serie(self, xml_detail):
        tmp = self.xpath_serie_condition(xml_detail)
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
        #TODO: book with one cover not found it, only with more
        tmp = self.xpath_cover(xml_detail)
        result = []
        if len(tmp) > 0:
            for cover in tmp:
                ident = cover.split("=")[-1]
                result.append('http://www.cbdb.cz/books/%s.jpg'%ident)
        if len(result) > 0:
            self.log('Found covers:%s'%result)
        else:
            self.log('Found covers:None')
        return result

    def download_detail(self):
        query = self.plugin.BASE_URL + self.ident
        br = self.browser
        try:
            self.log('download page detail %s'%query)
            data = br.open(query, timeout=self.timeout).read().strip()

            #fix, time limited action, broke HTML
            data = re.sub("ledna!</a></span>", b"ledna!</a>", data)

            self.devel.log_file(self.number, 'detail',  data)

            parser = etree.XMLParser(recover=True)
            clean = clean_ascii_chars(data)
            xml = fromstring(clean,  parser=parser)
            return xml
        except Exception as e:
            self.logexception('Failed to make download : %r'%query)
            return None

    def log(self, param):
        frame = inspect.getouterframes(inspect.currentframe(), 2)[1]
        self.logger.info('%s(%s): %s - %s'%(frame[3],frame[2],self.number, param))

    def logerror(self, param):
        frame = inspect.getouterframes(inspect.currentframe(), 2)[1]
        self.logger.error('%s(%s): %s - %s'%(frame[3],frame[2],self.number, param))

    def logexception(self, param):
        frame = inspect.getouterframes(inspect.currentframe(), 2)[1]
        self.logger.exception('%s(%s): %s - %s'%(frame[3],frame[2],self.number, param))

    def prepare_date(self,year):
        from calibre.utils.date import utc_tz
        return datetime.datetime(year, 1, 1, tzinfo=utc_tz)

