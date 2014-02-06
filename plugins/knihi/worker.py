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
from log import Log #REPLACE from calibre_plugins.knihi.log import Log
import re

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
        self.url = ident
        self.ident = re.search("\d+", ident).group()
        self.log = Log("worker %s"%self.ident, log)

    def initXPath(self):
        self.xpath_title = '//a[@class="odkaznadpis"]/text()'
        self.xpath_authors = '//table[@class="mezera"]//a[@class="odkazautor"]/text()'
        self.xpath_comments = '//table[@class="mezera"]//tr/td[last()]/text()'
        self.xpath_stars = '//span[@class="celkznamka"]/text()'
        self.xpath_category = '//div[@class="pruh"]/img[@alt="kategorie"]/following::text()[1]'
        self.xpath_tags = '//div[@class="stitek"]/a/@title'
        self.xpath_serie = '//div[@class="odkazy" and strong/text()="Série:"]'

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
        tags = self.parse_tags(xml_detail)
        serie, serie_index = self.parse_serie(xml_detail)

        if title is not None and authors is not None:
            mi = Metadata(title, authors)
            mi.languages = {'ces'}
            mi.comments = as_unicode(comments)
            mi.identifiers = {self.plugin.name:self.ident}
            mi.rating = rating
            mi.tags = tags
            mi.series = serie
            mi.series_index = serie_index
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
            self.log('Found authors:%s'%tmp)
            return tmp
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
            stars_ = int(tmp[0].replace('%',''))
            rating = float(stars_ / 20)
            self.log('Found rating:%s'%rating)
            return rating
        else:
            self.log('Found rating:None')
            return None

    def parse_tags(self, xml_detail):
        tags = []
        tags.extend(xml_detail.xpath(self.xpath_tags))
        tags.extend(xml_detail.xpath(self.xpath_category))

        if len(tags) > 0:
            self.log('Found tags:%s'%tags)
            return tags
        else:
            self.log('Found tags:None')
            return None

    def parse_serie(self, xml_detail):
        tmp = xml_detail.xpath(self.xpath_serie)
        if len(tmp) > 0:
            ch = tmp[0].getchildren()
            serie = ch[1].text
            serie_tmp = tmp[0].xpath('./text()')
            serie_index = 0
            for t in serie_tmp:
                if t.strip() != '':
                    serie_index = int(re.search("\d+", t).group())
            self.log('Found serie:%s[%d]'%(serie, serie_index))
            return [serie, serie_index]

        else:
            self.log('Found serie:None')
            return [None, None]

    def download_detail(self):
        query = self.plugin.BASE_URL + self.url
        br = self.browser
        try:
            self.log('download page detail %s'%query)
            data = br.open(query, timeout=self.timeout).read().strip()
            parser = etree.HTMLParser(recover = True)
#TODO: all parsers should use parser = etree.HTMLParser(recover = True)
            clean = clean_ascii_chars(data)
#             self.log.filelog(clean, "\\tmp\\worker%s.html"%self.ident)
            xml = fromstring(clean,  parser=parser)
            return xml
        except Exception as e:
            self.log.exception('Failed to make download : %r'%query)
            return None
