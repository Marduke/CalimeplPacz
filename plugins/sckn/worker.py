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
from functools import partial
from log import Log #REPLACE from calibre_plugins.sckn.log import Log
import datetime, urllib, re

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
        self.log = Log("worker %s"%ident, log)

    def run(self):
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
        data = xml_detail.split('\n')[1].split("|")
        self.log(data)

        title = data[1]
        authors = [data[0]]
        comments = data[13]
        isbn = data[3]
        publisher = data[6]
        pub_date_tmp = data[34].split('-')
        pub_date = datetime.datetime(int(pub_date_tmp[0]), int(pub_date_tmp[1]), int(pub_date_tmp[2]), tzinfo=utc_tz)
        if isbn is not None:
            isbn_tmp = re.sub("-", "", isbn)
            cover = "%s/images/covers/%s.jpg"%(self.plugin.BASE_URL, isbn_tmp)
        else:
            cover = None

        if title is not None and authors is not None:
            mi = Metadata(title, authors)
            mi.languages = {'ces'}
            mi.comments = as_unicode(comments)
            mi.identifiers = {self.plugin.name:self.ident}
            mi.publisher = publisher
            mi.pubdate = pub_date
            mi.isbn = isbn
            mi.cover_url = cover

            if cover:
                self.plugin.cache_identifier_to_cover_url(self.ident, cover)

            return mi
        else:
            return None

    def download_detail(self):
        url = "%shtml/csv_txt_export_hledani.php?dotaz=%s,0"%(self.plugin.BASE_URL, self.ident)
        parameters = {
            "vystup":"csv",
            "oddelovac":"pipe",
            "rozsah":"vse",
            "odeslano":"true"
        }
        query= [url, parameters]

        try:
            self.log('download page search %s'%query)
            data = urllib.urlencode(query[1])
            raw = self.browser.open(query[0],data,timeout=self.timeout).read().strip()
            clean = clean_ascii_chars(raw)
            return unicode(clean, 'cp1250')
        except Exception as e:
            self.log.exception('Failed to make identify query: %r'%query)
            return as_unicode(e)


