#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import, print_function)

__license__   = 'GPL v3'
__copyright__ = '2014, MarDuke <marduke@centrum.cz>'
__docformat__ = 'restructuredtext en'

from threading import Thread
from calibre.utils.cleantext import clean_ascii_chars
from calibre.ebooks.metadata.book.base import Metadata
from lxml import etree
from lxml.html import fromstring
from functools import partial
from UserString import MutableString
import datetime

NAMESPACES={
    'x':"http://www.w3.org/1999/xhtml"
}

#TODO: most relevant matches failed - fix!!! - relevance

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
        self.logger, self.relevance = log, relevance
        self.plugin, self.timeout = plugin, timeout
        self.cover_url = self.isbn = None
        self.devel = devel
        self.number = int(self.ident.split('-')[-1])
        self.XPath = partial(etree.XPath, namespaces=NAMESPACES)

    def run(self):
        #detail page has two parts
        #in broswer = page and ajax call for more info
        xml_detail = self.download_detail()
        xml_more_info = self.download_moreinfo()
        if xml_detail and xml_more_info:
            try:
                self.result_queue.put(self.parse(xml_detail, xml_more_info))
            except Exception as e:
                self.logexception(e)
        else:
            self.log('Download metadata failed for: %r'%self.ident)

    def parse(self, xml_detail, xml_more_info):
        title = self.parse_title(xml_detail)
        authors = self.parse_authors(xml_detail)
        comments = self.parse_comments(xml_detail)
        rating = self.parse_rating(xml_detail)
        isbn = self.parse_isbn(xml_more_info)
        publisher = self.parse_publisher(xml_more_info)
        tags = self.parse_tags(xml_detail, xml_more_info)
        serie, serie_index = self.parse_serie(xml_detail)
        pub_year = self.parse_pub_year(xml_detail, xml_more_info)
        cover = self.parse_cover(xml_detail)

        if title is not None and authors is not None:
            mi = Metadata(title, authors)
            mi.languages = {'ces'}
            mi.comments = comments
            mi.identifiers = {self.plugin.name:self.ident}
            mi.rating = rating
            mi.tags = tags
            mi.publisher = publisher
            mi.pubdate = pub_year
            mi.isbn = isbn
            mi.series = serie
            mi.seriesIndex = serie_index
            mi.cover_url = cover

            if cover:
                self.plugin.cache_identifier_to_cover_url(self.ident, cover)

            return mi

    def parse_title(self, xml_detail):
        title = self.XPath('//x:h1[contains(@class,"name")]/text()')
        tmp = title(xml_detail)
        if len(tmp) > 0:
            self.log('Found title:%s'%tmp[0])
            return tmp[0]
        else:
            self.log('Found title:None')
            return None

    def parse_authors(self, xml_detail):
        authors = self.XPath('//x:h2[@class="jmenaautoru"]/x:a/@title')
        tmp = authors(xml_detail)
        if len(tmp) > 0:
            self.log('Found authors:%s'%tmp)
            return tmp
        else:
            self.log('Found authors:None')
            return None

    def parse_comments(self, xml_detail):
        comments = self.XPath('//x:p[@id="biall"]')
        books_contains = self.XPath('//x:a[@class="h2" and starts-with(@href,"knihy/")]/text()')
        short_stories_url = self.XPath('//x:a[starts-with(@href, "povidky-z-knihy/")]/@href')
        short_stories_list = self.XPath('//x:table//x:a/@title')
        tmp = comments(xml_detail)

        result = MutableString()
        if len(tmp) > 0:
            result += "".join(tmp[0].xpath("text()"))

        tmp = books_contains(xml_detail)
        if len(tmp) > 0:
            result += "<p>Seznam knih ve kterých se povídka vyskytuje:<br/>"
            for book in tmp:
                result += book
                result += "<br/>"
            result += "</p>"

        tmp = short_stories_url(xml_detail)
        if len(tmp) > 0:
            xml_story_list = self.download_short_story_list(tmp[0])
            tmp2 = short_stories_list(xml_story_list)

            result += "<p>Seznam povídek:<br/>"
            for story in tmp2:
                result += story
                result += "<br/>"
            result += "</p>"

        if len(result) > 0:
            self.log('Found comment:%s'%result)
            return result
        else:
            self.log('Found authors:None')
            return None

    def parse_rating(self, xml_detail):
        stars = self.XPath('//x:a[@class="bpoints"]/text()')
        tmp = stars(xml_detail)
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

    def parse_isbn(self, xml_more_info):
        isbn = self.XPath('//strong[last()]/span/text()')
        tmp = isbn(xml_more_info)
        if len(tmp) > 0:
            self.log('Found ISBN:%s'%tmp[0])
            return tmp[0]
        else:
            self.log('Found authors:None')
            return None

    def parse_publisher(self, xml_more_info):
        publisher = self.XPath('//span[@itemprop="brand"]/a/text()')
        tmp = publisher(xml_more_info)
        if len(tmp) > 0:
            self.log('Found publisher:%s'%tmp[0])
            return tmp[0]
        else:
            self.log('Found publisher:None')
            return None

    def parse_tags(self, xml_detail, xml_more_info):
        tags = self.XPath('//x:span[@itemprop="category"]/text()')
        site_tags = self.XPath('//x:p[@class="binfo"][2]/x:a/@title')
        edition = self.XPath('//a[starts-with(@href, "edice/")]/text()')

        result = []

        tmp = tags(xml_detail)
        if len(tmp) > 0:
            result.extend(tmp[0].split(' - '))
            #TODO: add this also? to settings
            tmp2 = site_tags(xml_more_info)
            if len(tmp2) > 0:
                result.extend(tmp2)

        #TODO: settings povidka tag
        if self.ident.startswith('povidky/'):
            result.append('Povídka')

        #TODO: settings edice to tags
        tmp = edition(xml_more_info)
        if len(tmp) > 0:
            result.append(tmp[0])

        self.log('Found tags:%s'%result)
        return result

    def parse_serie(self, xml_detail):
        serie = self.XPath('//x:a[@class="strong" and starts-with(@href, "serie/")]')
        tmp = serie(xml_detail)

        if len(tmp) == 0:
            self.log('Found serie:None')
            return [None, None]

        xml_serie_index = self.download_serie_index(tmp[0].get('href'))
        serie_index = self.XPath('//x:a[@class="strong" and @href="%s"]/following-sibling::x:em[2]/x:strong/text()'%self.ident)
        if serie_index:
            tmp_index = serie_index(xml_serie_index)
            if len(tmp_index) > 0:
                self.log('Found serie:%s[%s]'%(tmp[0].text,tmp_index[0]))
                return [tmp[0], tmp_index[0]]
            else:
                self.log('Found serie:%s[None]'%tmp[0].text)
                return [tmp[0], None]
        else:
            return [tmp[0], None]

    def parse_pub_year(self, xml_detail, xml_more_info):
        pub_year_act = self.XPath('//x:p[@class="binfo odtop"]/x:strong[2]/text()')
        pub_year_first = self.XPath('//strong[1]/text()')
        #TODO: settings, switch to right source
        tmp = pub_year_act(xml_detail)
        #tmp = pub_year_first(xml_more_info)
        if len(tmp) > 0:
            res = self.prepare_date(int(tmp[0]))
            self.log('Found pub_date:%s'%res)
            return res
        else:
            self.log('Found pub_date:None')
            return self.prepare_date(1970)

    def parse_cover(self, xml_detail):
        cover = self.XPath('//x:img[@class="kniha_img"]/@src')
        tmp = cover(xml_detail)
        if len(tmp) > 0:
            self.log('Found cover:%s'%tmp[0])
            return tmp[0]
        else:
            self.log('Found cover:None')
            return None

    def download_detail(self):
        query = self.plugin.BASE_URL + self.ident
        br = self.browser
        try:
            self.log('download page detail %s'%query)
            data = br.open(query, timeout=self.timeout).read().strip()
            self.devel.log_file(self.number, 'detail',  data)

            parser = etree.XMLParser(recover=True)
            clean = clean_ascii_chars(data)
            xml = fromstring(clean,  parser=parser)
            return xml
        except Exception as e:
            self.logexception('Failed to make download : %r'%query)
            return None

    def download_moreinfo(self):
        query_more_info = '%shelpful/ajax/more_binfo.php?bid=%d'%(self.plugin.BASE_URL, self.number)
        try:
            self.log('download page moreinfo %s'%query_more_info)
            data = self.browser.open(query_more_info, timeout=self.timeout).read().strip()
            #fix - ajax request in not valid XML
            data = '<html>%s</html>'%data
            self.devel.log_file(self.number, 'moreInfo',  data)

            parser = etree.XMLParser(recover=True)
            clean = clean_ascii_chars(data)
            xml = fromstring(clean,  parser=parser)
            return xml
        except Exception as e:
            self.logexception('Failed to make download : %r'%query_more_info)
            return None

    def download_short_story_list(self, url):
        query_short_stories = self.plugin.BASE_URL + url
        try:
            self.log('download page with short stories list %s'%query_short_stories)
            data = self.browser.open(query_short_stories, timeout=self.timeout).read().strip()
            self.devel.log_file(self.number,'stories',  data)

            parser = etree.XMLParser(recover=True)
            clean = clean_ascii_chars(data)
            xml = fromstring(clean,  parser=parser)
            return xml
        except Exception as e:
            self.logexception('Failed to make download : %r'%query_short_stories)
            return None

    def download_serie_index(self, url):
        query_serie = self.plugin.BASE_URL + url
        try:
            self.log('download page with serie %s'%query_serie)
            data = self.browser.open(query_serie, timeout=self.timeout).read().strip()
            self.devel.log_file(self.number, 'serie_index',  data)

            parser = etree.XMLParser(recover=True)
            clean = clean_ascii_chars(data)
            xml = fromstring(clean,  parser=parser)
            return xml
        except Exception as e:
            self.logexception('Failed to make download : %r'%query_serie)
            return None

    def log(self, param):
        self.logger.info('%s - %s'%(self.number, param))

    def logerror(self, param):
        self.logger.error('%s - %s'%(self.number, param))

    def logexception(self, param):
        self.logger.exception('%s - %s'%(self.number, param))

    def prepare_date(self,year):
        from calibre.utils.date import utc_tz
        return datetime.datetime(year, 1, 1, tzinfo=utc_tz)

