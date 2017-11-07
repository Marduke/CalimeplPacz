#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import, print_function)
from locale import str

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
        self.xpath_title = self.XPath('//*[@itemprop="name"]/text()')
        self.xpath_authors = self.XPath('//a[@itemprop="author"]/text()')
        self.xpath_comments = self.XPath('//p[@itemprop="about"]')
        self.xpath_rating = self.XPath('//div[@id="item_rating"]/text()')
        self.xpath_isbn = self.XPath('//span[@itemprop="isbn"]/text()')
        self.xpath_publisher = self.XPath('//div[@class="book_info_line"]/a[starts-with(@href, "nakladatelstvi-")]/text()')
        self.xpath_pub_date = self.XPath('//div[@class="book_info_line"]/a[starts-with(@href, "nakladatelstvi-")]/following-sibling::text()[1]')
        self.xpath_tags = self.XPath('//span[@itemprop="genre"]/text()')
        self.xpath_serie = self.XPath('//a[@href="?show=serie"]/text()')
        self.xpath_serie_index = self.XPath('//a[@href="?show=serie"]/preceding-sibling::text()')
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
            self.log('Result skipped for because title or authors not found')
            return None

    def parse_title(self, xml_detail):
        tmp = self.xpath_title(xml_detail)
        if len(tmp) > 0:
            res = unicode(tmp[0])
            self.log('Found title:%s'%res)
            return res
        else:
            self.log('Found title:None')
            return None

    def parse_authors(self, xml_detail):
        tmp = self.xpath_authors(xml_detail)
        if len(tmp) > 0:
            self.log('Found authors:%s'%tmp)
            auths = []
            for author in tmp:
                auths.append(unicode(author))

            return auths
        else:
            self.log('Found authors:None')
            return None

    def parse_comments(self, xml_detail):
        tmp = self.xpath_comments(xml_detail)

        if len(tmp) > 0:
            #result = "".join(tmp[0].text).strip()
            result = unicode(tmp[0].text).strip()
            self.log('Found comment:%s'%result)

            return result
        else:
            self.log('Found comment:None')
            return None

    def parse_rating(self, xml_detail):
        tmp = self.xpath_rating(xml_detail)
        if len(tmp) > 0:
            rating = float(int(tmp[0].replace('%','')) / 20)
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
        tmpDate = self.xpath_pub_date(xml_detail)
        if len(tmp) > 0:
            publisher = tmp[0]
            pubDate = self.prepare_date(int(re.search('(\d+)', tmpDate[0]).group(0)))
            self.log('Found publisher:%s'%publisher)
            self.log('Found pub date:%s'%pubDate)
            return [publisher, pubDate]

        self.log('Found publisher:None')
        self.log('Found pub date:None')
        return (None, None)

    def parse_tags(self, xml_detail):
        tmp = self.xpath_tags(xml_detail)
        if len(tmp) > 0:
            result = tmp
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
        index = 0
        if self.plugin.prefs['serie_index']:
            tmpIndex = self.xpath_serie_index(xml_detail)
            index = int(re.search('(\d+)', tmpIndex[0]).group(0))

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
            cnt = num_add
            covers = self.plugin.prefs['max_covers']
            if covers:
                if cnt > covers:
                    cnt = covers
            for n in range(1,cnt):
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
            clean = clean_ascii_chars(data)
            self.log.filelog(clean, 'D:\\tmp\\file' + self.ident +'.html')
            xml = fromstring(clean, parser=parser)
#             for error in parser.error_log:
#                 self.log(error.message)
            return xml
        except Exception as e:
            self.log.exception('Failed to make download : %r'%query)
            return None

    def prepare_date(self,year):
        from calibre.utils.date import utc_tz
        return datetime.datetime(year, 1, 1, tzinfo=utc_tz)

