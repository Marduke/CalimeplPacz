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
from UserString import MutableString
from log import Log #REPLACE from calibre_plugins.dbknih.log import Log
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
        self.ident, self.result_queue = ident[0], result_queue
        self.browser = browser.clone_browser()
        self.relevance = relevance
        self.plugin, self.timeout = plugin, timeout
        self.cover_url = self.isbn = None
        self.number = int(self.ident.split('-')[-1])
        self.XPath = partial(etree.XPath, namespaces=plugin.NAMESPACES)
        self.log = Log("worker %i"%self.number, log)

    def initXPath(self):
        self.xpath_title = self.XPath('//x:h1[@itemprop="name"]/text()')
        self.xpath_authors = self.XPath('//x:span[@itemprop="author"]/x:a/text()')
        self.xpath_comments = self.XPath('//x:p[@id="bdetdesc"]//x:span')
        self.xpath_books_contains = self.XPath('//x:a[@class="h2" and starts-with(@href,"knihy/")]/text()')
        self.xpath_short_stories_url = self.XPath('//x:a[starts-with(@href, "povidky-z-knihy/")]/@href')
        self.xpath_short_stories_list = self.XPath('//x:table[@class="new morpad"]//x:a/@title')
        self.xpath_stars = self.XPath('//x:a[@class="bpoints"]/text()')
        self.xpath_isbn = self.XPath('//span[@itemprop="isbn"]/text()')
        self.xpath_publisher = self.XPath('//x:span[@itemprop="publisher"]/x:a/text()')
        self.xpath_tags = self.XPath('//x:h5[@itemprop="category"]/x:a/text()')
        self.xpath_site_tags = self.XPath('//x:a[starts-with(@href, "stitky/")]/text()')
        self.xpath_edition = self.XPath('//a[@itemprop="bookEdition"]/text()')
        self.xpath_serie = self.XPath('//x:a[starts-with(@href, "serie/")]/text()')
        self.xpath_serie_index = self.XPath('//x:a[starts-with(@href, "serie/")]/following-sibling::x:em/text()')
        self.xpath_pub_year_act = self.XPath('//x:span[@itemprop="datePublished"]/text()')
        self.xpath_pub_year_first = self.XPath('/x:span[@itemprop="datePublished"]/following-sibling::strong[1]/text()')
        self.xpath_cover = self.XPath('//x:img[@class="kniha_img"]/@src')


    def run(self):
        self.initXPath()
        #detail page has two parts
        #in broswer = page and ajax call for more info
        xml_detail = self.download_detail()
        xml_more_info = self.download_moreinfo()
        if xml_detail is not None and xml_more_info is not None:
            try:
                self.result_queue.put(self.parse(xml_detail, xml_more_info))
            except Exception as e:
                self.log.exception(e)
        else:
            self.log('Download metadata failed for: %r'%self.ident)

    def parse(self, xml_detail, xml_more_info):
        title = self.parse_title(xml_detail)
        authors = self.parse_authors(xml_detail)
        comments = self.parse_comments(xml_detail)
        rating = self.parse_rating(xml_detail)
        isbn = self.parse_isbn(xml_more_info)
        publisher = self.parse_publisher(xml_detail)
        tags = self.parse_tags(xml_detail, xml_more_info)
        serie, serie_index = self.parse_serie(xml_detail)
        pub_year = self.parse_pub_year(xml_detail, xml_more_info)
        cover = self.parse_cover(xml_detail)

        if title is not None and authors is not None:
            mi = Metadata(as_unicode(title), authors)
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
            self.log('Result skipped for because title or authors not found')
            return None

    def parse_title(self, xml_detail):
        tmp = self.xpath_title(xml_detail)
        if len(tmp) > 0:
            self.log('Found title:%s'%tmp[0])
            return unicode(tmp[0])
        else:
            self.log('Found title:None')
            return None

    def parse_authors(self, xml_detail):
        tmp = self.xpath_authors(xml_detail)
        if len(tmp) > 0:
            result = []
            for author in tmp:
                result.append(unicode(author))
            self.log('Found authors:%s'%result)
            return result
        else:
            self.log('Found authors:None')
            return None

    def parse_comments(self, xml_detail):
        tmp = self.xpath_comments(xml_detail)

        result = MutableString()
        if len(tmp) > 0:
            result += "".join(tmp[0].xpath("text()"))
        self.log('Found comment:%s'%result)

        if self.plugin.prefs['add_mother_book_list']:
            tmp = self.xpath_books_contains(xml_detail)
            if len(tmp) > 0:
                result += "<p>Seznam knih ve kterých se povídka vyskytuje:<ul>"
                for book in tmp:
                    result += "<li>"
                    result += book
                    result += "</li>"
                result += "</ul></p>"

        if self.plugin.prefs['add_short_story_list']:
            tmp = self.xpath_short_stories_url(xml_detail)
            if len(tmp) > 0:
                xml_story_list = self.download_short_story_list(tmp[0])
                tmp2 = self.xpath_short_stories_list(xml_story_list)

                result += "<p>Seznam povídek:<ul>"
                for story in tmp2:
                    result += "<li>"
                    result += story
                    result += "</li>"
                result += "</ul></p>"

        if len(result) > 0:
            self.log('Found comment with addings:%s'%result)
            return unicode(result)
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

    def parse_isbn(self, xml_more_info):
        tmp = self.xpath_isbn(xml_more_info)
        if len(tmp) > 0:
            isbn = tmp[0]
            if "," in isbn:
              isbn = isbn.split(',')[0]
            self.log('Found ISBN:%s'%isbn)
            return unicode(isbn)
        else:
            self.log('Found ISBN:None')
            return None

    def parse_publisher(self, xml_more_info):
        tmp = self.xpath_publisher(xml_more_info)
        if len(tmp) > 0:
            self.log('Found publisher:%s'%tmp[0])
            return unicode(tmp[0])
        else:
            self.log('Found publisher:None')
            return None

    def parse_tags(self, xml_detail, xml_more_info):
        result = []

        tmp = self.xpath_tags(xml_detail)
        if len(tmp) > 0:
            for tag in tmp:
              result.append(unicode(tag))
        if self.plugin.prefs['parse_tags']:
            tmp2 = self.xpath_site_tags(xml_detail)
            if len(tmp2) > 0:
                for tag in tmp2:
                  result.append(unicode(tag))

        if self.plugin.prefs['short_story']:
            if self.ident.startswith('povidky/'):
                result.append(u'Povídka')

        if self.plugin.prefs['short_story_collection']:
            tmp = self.xpath_short_stories_url(xml_detail)
            if len(tmp) > 0:
                result.append(u'Sbírka povídek')

        if self.plugin.prefs['edition']:
            tmp = self.xpath_edition(xml_more_info)
            if len(tmp) > 0:
                result.append(unicode(self.plugin.prefs['edition_prefix']+tmp[0]))

        self.log('Found tags:%s'%result)
        return result

    def parse_serie(self, xml_detail):
        tmp = self.xpath_serie(xml_detail)
        
        if len(tmp) == 0:
            self.log('Found serie:None')
            return [None, None]

        serie_index = self.xpath_serie_index(xml_detail)
        if len(serie_index) > 0:
            index = re.sub('[,.() ]', '', serie_index[0])
            self.log('Found serie:%s[%s]'%(tmp[0], index))
            return [unicode(tmp[0]), index]
        else:
            self.log('Found serie:%s'%tmp[0])
            return [unicode(tmp[0]), None]

    def parse_pub_year(self, xml_detail, xml_more_info):
        if self.plugin.prefs['pub_date'] == 'Poslední datum vydání':
            tmp = self.xpath_pub_year_act(xml_detail)
        elif self.plugin.prefs['pub_date'] == 'První datum vydání':
            tmp = self.xpath_pub_year_first(xml_more_info)

        if len(tmp) > 0:
            res = self.prepare_date(int(tmp[0]))
            self.log('Found pub_date:%s'%res)
            return res
        else:
            self.log('Found pub_date:None')
            return self.prepare_date(1970)

    def parse_cover(self, xml_detail):
        tmp = self.xpath_cover(xml_detail)
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
            parser = etree.XMLParser(recover=True)
            clean = clean_ascii_chars(data)
            xml = fromstring(clean,  parser=parser)
            return xml
        except Exception as e:
            self.log.exception('Failed to make download : %r'%query)
            return None

    def download_moreinfo(self):
        query_more_info = '%shelpful/ajax/more_binfo.php?bid=%d'%(self.plugin.BASE_URL, self.number)
        try:
            self.log('download page moreinfo %s'%query_more_info)
            data = self.browser.open(query_more_info, timeout=self.timeout).read().strip()
            #fix - ajax request in not valid XML
            data = '<html>%s</html>'%data
            parser = etree.XMLParser(recover=True)
            clean = clean_ascii_chars(data)
            xml = fromstring(clean,  parser=parser)
            return xml
        except Exception as e:
            self.log.exception('Failed to make download : %r'%query_more_info)
            return None

    def download_short_story_list(self, url):
        query_short_stories = self.plugin.BASE_URL + url
        try:
            self.log('download page with short stories list %s'%query_short_stories)
            data = self.browser.open(query_short_stories, timeout=self.timeout).read().strip()
            parser = etree.XMLParser(recover=True)
            clean = clean_ascii_chars(data)
            xml = fromstring(clean,  parser=parser)
            return xml
        except Exception as e:
            self.log.exception('Failed to make download : %r'%query_short_stories)
            return None

    def prepare_date(self,year):
        from calibre.utils.date import utc_tz
        return datetime.datetime(year, 1, 1, tzinfo=utc_tz)

