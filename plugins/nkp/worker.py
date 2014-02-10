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
        if self.ident.startswith("http"):
            self.url = self.ident
            num = re.search("set_entry=\d+", self.ident).group().split('=')[1]
            self.ident = num
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
        sys_ident = title = isbn = publisher = pub_year = serie = serie_index = cover = None
        authors = []
        tags = []
        xpath = self.XPath('//table[@id="record"]//tr')
        for row in xpath(xml_detail):

            ch = row.getchildren()
            txt = ch[0].text.strip()
            data = self.normalize(ch[1].text)
            if txt.startswith('245') and title is None:
                title = self.parse_title(data)
            elif txt.startswith('100') or txt.startswith('700'):
                authors.append(self.parse_author(data))
            elif txt == 'SYS':
                sys_ident = data
            elif txt =='020':
                isbn = self.parse_isbn(data)
            elif txt == '260':
                publisher, pub_year = self.parse_publisher(data)
            elif txt.startswith('490') and serie is None:
                serie, serie_index = self.parse_serie(data)
            elif txt == '655 7':
                tags.append(self.parse_tags(data))

        if isbn is not None and isbn != '':
            cover = self.parse_cover(isbn)

        if title is not None and len(authors) > 0 and sys_ident is not None:
            mi = Metadata(title, authors)
            mi.languages = {'ces'}
            mi.identifiers = {self.plugin.name:sys_ident}
            mi.tags = tags
            mi.publisher = publisher
            mi.pubdate = pub_year
            mi.isbn = isbn
            mi.series = serie
            mi.series_index = serie_index
            mi.cover_url = cover

            if cover:
                self.log("store cached img %s for %s"%(cover, sys_ident))
                self.plugin.cache_identifier_to_cover_url(sys_ident, cover)

            return mi
        else:
            self.log('Data not found')
            return None

    def parse_title(self, data):
        title = data['a'].split('/')[0]
        self.log('Found title:%s'%title)
        return title

    def parse_author(self, data):
        parts = data['a'].split(',')
        filtred = []
        for part in parts:
            tmp = part.strip()
            if tmp != '':
                filtred.append(tmp)
        author = " ".join(filtred[1:]).strip() + " " + filtred[0]
        self.log('Found author:%s'%author)
        return author

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
        isbn = data['a'].strip().split(' ')[0].strip()
        if self.isbn_valid(isbn):
            self.log('Found ISBN:%s'%isbn)
            return isbn
        else:
            self.log('Found invalid ISBN:%s skiped...'%isbn)
            return None

    def isbn_valid(self, isbn):
        num = 0
        for c in isbn:
            if c >= '0' and c <= '9':
                num += 1
            elif c == '-':
                pass
            else:
                return False
        return num == 10 or num == 13

    def parse_publisher(self, data):
        publisher = data['b'].split(',')[0]
        pub_date = self.prepare_date(int(re.search("\d+", data['c']).group()))
        self.log('Found publisher:%s'%publisher)
        self.log('Found pub date:%s'%pub_date)
        return [publisher, pub_date]

    def parse_tags(self, data):
        tag = data['a'].strip()
        self.log('Found tag:%s'%tag)
        return tag

    def parse_serie(self, data):
        serie = data['a'].split(';')[0].strip()
        if data.has_key('v'):
            serie_index = re.search("\d+", data['v']).group()
        else:
            serie_index = 0
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

        if len(data) > 0:
            url = re.search('cover_url:".*"', data).group()
            url = url[11:-1]
            self.log("Found cover:%s"%url)
            return url
        return None

    def download_detail(self):
        if self.url is None:
            query = self.plugin.BASE_URL + self.ident
        else:
            query = re.sub("format=999", "format=001", self.url)
        br = self.browser
        try:
            self.log('download page detail %s'%query)
            data = br.open(query, timeout=self.timeout).read().strip()
            parser = etree.HTMLParser(recover=True)
            clean = clean_ascii_chars(data)
            xml = fromstring(clean,  parser=parser)
            return xml
        except Exception as e:
            self.log.exception('Failed to make download : %r'%query)
            return None

    def normalize(self, txt):
        if txt is None:
            return None
        if '|' in txt:
            result = {}
            parts = txt.split('|')
            for tmp in parts[1:]:
                result[tmp[0]] = tmp[1:].strip()
            return result
        else:
            return txt

    def prepare_date(self,year):
        from calibre.utils.date import utc_tz
        return datetime.datetime(year, 1, 1, tzinfo=utc_tz)

