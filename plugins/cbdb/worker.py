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
from log import Log #REPLACE from calibre_plugins.cbdb.log import Log
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
        if xml is not None:
            self.number = int(ident)
        else:
            self.number = int(self.ident.split('-')[1])

        self.log = Log("worker %i"%self.number, log)

    def initXPath(self):
        self.xpath_title = self.XPath('//span[@itemprop="name"]/text()')
        self.xpath_authors = self.XPath('//a[@itemprop="author"]/text()')
        self.xpath_comments = self.XPath('//div[@id="book_description"]/text()')
        self.xpath_stars = self.XPath('//div[@id="book_rating"]/text()')
        self.xpath_isbn = self.XPath('//div[@id="book_releases"]//tr/td[2]/text()')
        self.xpath_publisher = self.XPath('//div[@id="book_releases"]//tr/td[1]/text()')
        self.xpath_tags = self.XPath('//div[@id="book_kinds"]//span/text()')
        self.xpath_serie = self.XPath('//div[@id="book_right_serie"]/h4/text()')
        self.xpath_serie_index = self.XPath('//div[@id="book_right_serie"]/ul/li[@class="list_0"]')
        self.xpath_cover = self.XPath('//div[@id="book_covers_control"]/@onclick')

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
            self.log('Download metadata failed for: %r'%self.ident)

    def parse(self, xml_detail):
        title = self.parse_title(xml_detail)
        authors = self.parse_authors(xml_detail)
        comments = self.parse_comments(xml_detail)
        rating = self.parse_rating(xml_detail)
        isbn = self.parse_isbn(xml_detail)
        publisher, pub_year = self.parse_publisher(xml_detail)
        tags = self.parse_tags(xml_detail)
        serie, serie_index = self.parse_serie(xml_detail, title)
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
            stars_ = int(tmp[0].replace('%',''))
            rating = float(stars_ / 20)
            self.log('Found rating:%s'%rating)
            return rating
        else:
            self.log('Found rating:None')
            return None

    def parse_isbn(self, xml_detail):
        tmp = self.xpath_isbn(xml_detail)
        if len(tmp) > 0:
            self.log('Found ISBN:%s'%tmp[0].strip())
            return tmp[0].strip()
        else:
            self.log('Found ISBN:None')
            return None

    def parse_publisher(self, xml_detail):
        tmp = self.xpath_publisher(xml_detail)
        if len(tmp) > 0:
            data = tmp[0].strip().split('\n')
            if len(data) == 2:
                self.log('Found publisher:%s'%data[0])
                date_string = re.search('(\d+)',data[1]).group(0)
                self.log('Found pub date:%s'%date_string)
                data[1] = self.prepare_date(int(date_string))
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

    def parse_serie(self, xml_detail, title):
        tmp = self.xpath_serie(xml_detail)
        if len(tmp) == 0:
            self.log('Found serie:None')
            return [None, None]
        else:
            index = 0
            if self.plugin.prefs['serie_index']:
                tag_list = self.xpath_serie_index(xml_detail)
                for tag in tag_list:
                    if tag.find('.//a').text == title:
                        index = int(re.search('(\d+)', tag.find('span').text.strip()).group(0))

            self.log('Found serie:%s[%i]'%(tmp[0],index))
            return [tmp[0], index]

    def parse_cover(self, xml_detail):
        tmp = self.xpath_cover(xml_detail)
        result = []
        if len(tmp) > 0:
            nums = re.findall('\d+', tmp[0])
            ident = int(nums[0])
            num_add = int(nums[1])
            result.append(self.plugin.BASE_URL + 'books/%i.jpg'%ident)
            for n in range(1,num_add):
                result.append(self.plugin.BASE_URL + 'books/%i_%i.jpg'%(ident, n))

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
            parser = etree.HTMLParser(recover=True)
            raw = data.decode('utf-8', errors='replace')
            clean = clean_ascii_chars(raw)
            xml = fromstring(clean, parser=parser)
            return xml
        except Exception as e:
            self.log.exception('Failed to make download : %r'%query)
            return None

    def prepare_date(self,year):
        from calibre.utils.date import utc_tz
        return datetime.datetime(year, 1, 1, tzinfo=utc_tz)

