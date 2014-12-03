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
from UserString import MutableString
from log import Log #REPLACE from calibre_plugins.legie.log import Log
import datetime

from calibre.utils.icu import lower

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
        self.xpath_title = self.XPath('//x:h2[@id="nazev_knihy"]/text()')
        self.xpath_title_story = self.XPath('//x:h2[@id="nazev_povidky"]/text()')
        self.xpath_authors = self.XPath('//x:a[starts-with(@href,"autor/")]/text()')
        self.xpath_comments_serie = self.XPath('//x:div[@id="anotace"]/x:p//text()')
        self.xpath_comments = self.XPath('//x:div[@id="detail"]/x:div[@id="nic"]/x:p//text()')
        self.xpath_stars = self.XPath('//x:div[@id="procenta"]/x:span[1]/text()')
        self.xpath_isbn = self.XPath('//x:div[@class="vydani cl"]//x:span[starts-with(@title, "ISBN")]/following::text()')
        self.xpath_publisher = self.XPath('//x:div[@class="data_vydani"]//x:a[starts-with(@href, "vydavatel/")]/text()')
        self.xpath_pub_date = self.XPath('//x:div[@class="data_vydani"]/x:table/x:tbody/x:tr/x:td[starts-with(text(), "přibl")]/text()')
        #self.xpath_tags = self.XPath('//x:div[@id="kniha_info"]//x:a[starts-with(@href, "tagy/")]/text()')
        self.xpath_tags = self.XPath('//x:a[starts-with(@href, "tagy/")]/text()')
        self.xpath_serie = self.XPath('//x:div[@id="kniha_info"]//x:a[starts-with(@href, "serie/")]/text()')
        self.xpath_serie_index = self.XPath('//x:div[@id="kniha_info"]//x:a[starts-with(@href, "serie/")]/following-sibling::text()[1]')
        self.xpath_cover = self.XPath('//x:div[@id="vycet_vydani"]//x:img[@class="obalk"]/@src')
        self.xpath_world = self.XPath('//x:div[@id="kniha_info"]//x:a[starts-with(@href, "svet/")]/text()')
        self.xpath_contain_story = self.XPath('//x:div[@id="zarazena_do_knih"]/child::*[text()]')

    def run(self):
        self.initXPath()

        if self.xml is not None:
            xml_detail = self.xml
        else:
            xml_detail = self.download_detail()
        xml_releases = self.download_releases()
        if xml_detail is not None and xml_releases is not None:
            try:
                result = self.parse(xml_detail, xml_releases)
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
            mi.identifiers = {self.plugin.name:self.ident}
            mi.rating = rating
            mi.tags = tags
            mi.publisher = publisher
            mi.pubdate = pub_date
            mi.isbn = isbn
            mi.series = serie
            mi.series_index = serie_index
            mi.cover_url = cover

            if cover is not None:
                self.plugin.cache_identifier_to_cover_url(self.ident, cover)

            return mi
        else:
            return None

    def parse_title(self, xml_detail):
        tmp = self.xpath_title(xml_detail)
        if len(tmp) > 0:
            title = unicode(tmp[0])
            self.log('Found title:%s'%title)
            return title
        else:
            tmp = self.xpath_title_story(xml_detail)
            if len(tmp) > 0:
                self.log('Found title:%s'%tmp[0])
                return tmp[0]
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
        result = MutableString()

        tmp = self.xpath_comments(xml_detail)
        if len(tmp) > 0:
            result += "<br/>".join(tmp).strip()

        tmp = self.xpath_comments_serie(xml_detail)
        if len(tmp) > 0:
            result += "<br/>".join(tmp).strip()

        if self.plugin.prefs['add_mother_book_list']:
            tmp = self.xpath_contain_story(xml_detail)
            if len(tmp) > 0:
                result += "<p>Povídka je obsažena v knihách:<ul>"
                for txt in tmp:
                    if txt.tag == "{http://www.w3.org/1999/xhtml}a":
                        result +="<li>"
                        result += txt.text
                        result +="</li>"
                    else:
                        result += "pod jmnénem "
                        result += txt.text
                result += "</ul></p>"

        self.log('Found comment:%s'%result)
        return result

    def parse_rating(self, xml_detail):
        tmp = self.xpath_stars(xml_detail)
        if len(tmp) > 0:
            stars_ = int(tmp[0])
            rating = float(stars_ / 20)
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
        if self.plugin.prefs['world_tag']:
            tmp = self.xpath_world(xml_detail)
            if len(tmp) > 0:
                self.log('Found world:%s'%tmp[0])
                tags += [self.plugin.prefs['world_tag_prefix']+tmp[0]]

        if self.plugin.prefs['short_story']:
            if self.ident.startswith('povidka'):
                tags.append('povidka')

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
        query = self.plugin.BASE_URL+self.ident
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

    def download_releases(self):
        query = self.plugin.BASE_URL + self.ident + "/vydani"
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