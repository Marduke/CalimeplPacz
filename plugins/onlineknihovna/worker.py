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
from log import Log #REPLACE from calibre_plugins.onlineknihovna.log import Log
import datetime, re

#Single Thread to process one page of searched list
class Worker(Thread):

    #string id
    ident = None

    #int id
    number = None

    def __init__(self, ident, result_queue, browser, log, relevance, plugin, devel, timeout=20):
        Thread.__init__(self)
        self.daemon = True
        self.ident, self.result_queue = ident, result_queue
        self.browser = browser.clone_browser()
        self.devel, self.relevance = devel, relevance
        self.plugin, self.timeout = plugin, timeout
        self.cover_url = self.isbn = None
        self.XPath = partial(etree.XPath, namespaces=plugin.NAMESPACES)
        self.number = int(self.ident.split('/')[-1])
        self.log = Log("worker %i"%self.number, log, True)

    def initXPath(self):
        self.xpath_title = '//div[@class="row"]/div[@class="span3 text-right" and starts-with(strong/p/text(),"Název")]/following-sibling::div[1]/p/text()'
        self.xpath_authors = '//div[@class="row"]/div[@class="span3 text-right" and starts-with(strong/p/text(),"Autor")]/following-sibling::div[1]/p/a/text()'
        self.xpath_comments = '//div[@class="row"]/div[@class="span3 text-right" and starts-with(strong/p/text(),"Anotace")]/following-sibling::div[1]/div/text()'
        self.xpath_stars = self.XPath('//x:span[@id="book_rating_text"]/text()')
        self.xpath_isbn = '//div[@class="row"]/div[@class="span3 text-right" and starts-with(strong/p/text(),"ISBN")]/following-sibling::div[1]/p/text()'
        self.xpath_publisher = self.XPath('//x:span[@itemprop="isbn"]/preceding-sibling::text()')
        self.xpath_tags = self.XPath('//x:td[@class="v_top"]/x:strong[2]/text()')
        self.xpath_serie_condition = self.XPath('//x:div[@id="right"]/x:fieldset[1]/x:legend/text()')
        self.xpath_serie = self.XPath('//x:div[@id="right"]/x:fieldset[1]/x:div/x:strong/text()')
        self.xpath_serie_index = self.XPath('//x:div[@id="right"]/x:fieldset[1]//x:div[@class="right_book"]/x:a/@href')
        self.xpath_cover = '//div[@class="row"]/div[@class="span3 text-right imag" and starts-with(strong/p/text(),"Obrázek")]/following-sibling::div[1]/a/p/img/@src'

    def run(self):
        self.initXPath()

        xml_detail = self.download_detail()
        if xml_detail is not None:
            try:
                result = self.parse(xml_detail)
                if result:
                    self.result_queue.put(result)
            except Exception as e:
                self.log.exception(e)
        else:
            self.log.info('Download metadata failed for: %s'%self.ident)

        self.log.digg()

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
        tmp = xml_detail.xpath(self.xpath_title)
        if len(tmp) > 0:
            self.log.info('Found title:%s'%tmp[0])
            return tmp[0]
        else:
            self.log.info('Found title:None')
            return None

    def parse_authors(self, xml_detail):
        tmp = xml_detail.xpath(self.xpath_authors)
        if len(tmp) > 0:
            self.log.info('Found authors:%s'%tmp)
            return tmp
        else:
            self.log.info('Found authors:None')
            return None

    def parse_comments(self, xml_detail):
        #TODO: wuut
        tmp = xml_detail.xpath(self.xpath_comments)
        self.log.info(tmp)
        if len(tmp) > 0:
            self.log.info(tmp[0])
            result = "".join(tmp).strip()
            self.log.info('Found comment:%s'%result)
            return result
        else:
            self.log.info('Found comment:None')
            return None

    def parse_rating(self, xml_detail):
        tmp = self.xpath_stars(xml_detail)
        if len(tmp) > 0:
            stars_ = int(tmp[0].replace(' %',''))
            rating = int(stars_ / 20)
            if stars_ % 20 > 0:
                rating += 1
            self.log.info('Found rating:%s'%rating)
            return rating
        else:
            self.log.info('Found rating:None')
            return None

    def parse_isbn(self, xml_detail):
        tmp = xml_detail.xpath(self.xpath_isbn)
        if len(tmp) > 0:
            self.log.info('Found ISBN:%s'%tmp[0])
            return tmp[0]
        else:
            self.log.info('Found ISBN:None')
            return None

    def parse_publisher(self, xml_more_info):
        tmp = self.xpath_publisher(xml_more_info)
        if len(tmp) > 0:
            data = tmp[-2].strip().split(' - ')
            if len(data) == 2:
                self.log.info('Found publisher:%s'%data[0])
                self.log.info('Found pub date:%s'%data[1])
                data[1] = self.prepare_date(int(data[1]))
                return data

        self.log.info('Found publisher:None')
        self.log.info('Found pub date:None')
        return (None, None)

    def parse_tags(self, xml_detail):
        tmp = self.xpath_tags(xml_detail)
        if len(tmp) > 0:
            result = tmp[0].split(' / ')
            self.log.info('Found tags:%s'%result)
            return result
        else:
            self.log.info('Found tags:None')
            return None

    def parse_serie(self, xml_detail):
        tmp = self.xpath_serie_condition(xml_detail)
        if len(tmp) == 0 or not tmp[0] == 'Série':
            self.log.info('Found serie:None')
            return [None, None]

        tmp = self.xpath_serie(xml_detail)
        if len(tmp) == 0:
            self.log.info('Found serie:None')
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

            self.log.info('Found serie:%s[%i]'%(tmp[0],index))
            return [tmp[0], index]

    def parse_cover(self, xml_detail):
        tmp = xml_detail.xpath(self.xpath_cover)
        self.log.info(tmp)
        if len(tmp) > 0:
            self.log.info('Found covers:%s'%tmp[0])
            return tmp[0]
        else:
            self.log.info('Found covers:None')

    def download_detail(self):
        query = self.plugin.BASE_URL + self.ident
        br = self.browser
        try:
            self.log.info('download page detail %s'%query)
            data = br.open(query, timeout=self.timeout).read().strip()

            self.devel.log_file(self.number, 'detail',  data)

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

