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
from log import Log #REPLACE from calibre_plugins.kdb.log import Log
import datetime, re

#Single Thread to process one page of searched list
class Worker(Thread):

    #string id
    ident = None

    #int id
    number = None

    def __init__(self, ident, result_queue, browser, log, relevance, plugin, timeout=20):
        Thread.__init__(self)
        self.daemon = True
        self.ident, self.result_queue = ident, result_queue
        self.browser = browser.clone_browser()
        self.relevance = relevance
        self.plugin, self.timeout = plugin, timeout
        self.cover_url = self.isbn = None
        self.XPath = partial(etree.XPath, namespaces=plugin.NAMESPACES)
        self.number = int(ident)
        self.log = Log("worker %i"%self.number, log)

    def initXPath(self):
        #TODO:
        self.xpath_title = self.XPath('//x:h2[@id="nazev_knihy"]/text()')
        #TODO:
        self.xpath_authors = self.XPath('//x:a[starts-with(@href,"autor/")]/text()')
        #TODO:
        self.xpath_comments = self.XPath('//x:div[@id="anotace"]/x:p//text()')
        #TODO:
        self.xpath_stars = self.XPath('//x:div[@id="procenta"]/text()')
        #TODO:
        self.xpath_isbn = self.XPath('//x:div[@class="vydani cl"]//x:span[starts-with(@title, "ISBN")]/following::text()')
        #TODO:
        self.xpath_publisher = self.XPath('//x:div[@class="data_vydani"]//x:a[starts-with(@href, "vydavatel/")]/text()')
        #TODO:
        self.xpath_pub_date = self.XPath('//x:div[@class="data_vydani"]/x:table/x:tbody/x:tr/x:td[starts-with(text(), "přibl")]/text()')
        #TODO:
        self.xpath_tags = self.XPath('//x:div[@id="kniha_info"]//x:a[starts-with(@href, "tagy/")]/text()')
        #TODO:
        self.xpath_serie = self.XPath('//x:div[@id="kniha_info"]//x:a[starts-with(@href, "serie/")]/text()')
        #TODO:
        self.xpath_serie_index = self.XPath('//x:div[@id="kniha_info"]//x:a[starts-with(@href, "serie/")]/following-sibling::text()[1]')
        #TODO:
        self.xpath_cover = self.XPath('//x:div[@id="vycet_vydani"]//x:img[@class="obalk"]/@src')
        #TODO:
        self.xpath_world = self.XPath('//x:div[@id="kniha_info"]//x:a[starts-with(@href, "svet/")]/text()')

    def run(self):
        self.initXPath()

        xml_detail = self.download_detail()
        xml_covers = self.download_covers()
        if xml_detail is not None and xml_covers is not None:
            try:
                result = self.parse(xml_detail, xml_covers)
                if result:
                    self.result_queue.put(result)
            except Exception as e:
                self.log.exception(e)
        else:
            self.log('Download metadata failed for: %r'%self.ident)

    def parse(self, xml_detail, xml_releases):
        title = self.parse_title(xml_detail)
        authors = self.parse_authors(xml_detail)
        comments = self.parse_comments(xml_detail)
        rating = self.parse_rating(xml_detail)
        isbn = self.parse_isbn(xml_releases)
        publisher = self.parse_publisher(xml_releases)
        pub_date = self.parse_pub_date(xml_releases)
        tags = self.parse_tags(xml_detail)
        serie, serie_index = self.parse_serie(xml_detail)
        cover = self.parse_cover(xml_releases)

        if title is not None and authors is not None:
            mi = Metadata(title, authors)
            mi.languages = {'ces'}
            mi.comments = as_unicode(comments)
            mi.identifiers = {self.plugin.name:str(self.number)}
            mi.rating = rating
            mi.tags = tags
            mi.publisher = publisher
            mi.pubdate = pub_date
            mi.isbn = isbn
            mi.series = serie
            mi.series_index = serie_index
            mi.cover_url = cover

            if cover is not None:
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
            result = "<br/>".join(tmp).strip()
            self.log('Found comment:%s'%result)
            return result
        else:
            self.log('Found comment:None')
            return None

    def parse_rating(self, xml_detail):
        tmp = self.xpath_stars(xml_detail)
        if len(tmp) > 0:
            stars_ = int(tmp[0].replace('%',''))
            rating = int(stars_ / 20)
            if stars_ % 20 > 0:
                rating += 1
            self.log('Found rating:%s'%rating)
            return rating
        else:
            self.log('Found rating:None')
            return None

    def parse_isbn(self, xml_releases):
        tmp = self.xpath_isbn(xml_releases)
        if len(tmp) > 0:
            isbn = tmp[1].strip()
            self.log('Found ISBN:%s'%isbn)
            return isbn
        else:
            self.log('Found ISBN:None')
            return None

    def parse_publisher(self, xml_releases):
        tmp = self.xpath_publisher(xml_releases)
        if len(tmp) > 0:
            self.log('Found publisher:%s'%tmp[0])
            return tmp[0]

        self.log('Found publisher:None')
        return None

    def parse_pub_date(self, xml_releases):
        tmp = self.xpath_pub_date(xml_releases)
        if len(tmp) > 0:
            dt = tmp[-1].strip()
            self.log('Found pub_date:%s'%dt)
            dates = dt.split(".")
            return datetime.datetime(int(dates[2]), int(dates[1]), int(dates[0]), tzinfo=utc_tz)

        self.log('Found pub_date:None')
        return None

    def parse_tags(self, xml_detail):
        tags = []
        tags += self.xpath_tags(xml_detail)
        self.log('Found tags:%s'%tags)
        return tags

    def parse_serie(self, xml_detail):
        tmp = self.xpath_serie(xml_detail)
        if len(tmp) == 0:
            self.log('Found serie:None')
            return [None, None]
        else:
            index = 0
            tmp_index = self.xpath_serie_index(xml_detail)
            if len(tmp_index) > 0:
                index = int(tmp_index[0].split(' ')[-1])
            self.log('Found serie:%s[%i]'%(tmp[0],index))
            return [tmp[0], index]

    def parse_cover(self, xml_releases):
        tmp = self.xpath_cover(xml_releases)
        if len(tmp) > 0:
            result = [self.plugin.BASE_URL + url for url in tmp]
            self.log('Found covers:%s'%result)
            return result
        else:
            self.log('Found covers:None')
            return None

    def download_detail(self):
        query = "%skniha-%s"%(self.plugin.BASE_URL,self.ident)
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

    def download_covers(self):
        query = "%skniha-%s/obalky"%(self.plugin.BASE_URL,self.ident)
        br = self.browser
        try:
            self.log('download page releases %s'%query)
            data = br.open(query, timeout=self.timeout).read().strip()
            parser = etree.XMLParser(recover=True)
            clean = clean_ascii_chars(data)
            xml = fromstring(clean,  parser=parser)
            return xml
        except Exception as e:
            self.log.exception('Failed to make download : %r'%query)
            return None