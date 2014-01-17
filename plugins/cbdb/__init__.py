#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import, print_function)
from html5lib.treebuilders import etree_lxml

__license__   = 'GPL v3'
__copyright__ = '2014, MarDuke <marduke@centrum.cz>'
__docformat__ = 'restructuredtext en'

#TODO: settings - add to short story tag?
#TODO: settings - parse tags and categories OR only categs - may spam tags
#TODO: settings - edice into tags
#TODO: settings - max processed books in serach - 0 = all
#TODO: settings - parse year from actual publish year or first publish year
#TODO: settings - parse short stories list and store it at end of comment
#TODO: settings - for short stories parse list of book which include it and add it and end of comment

import re, time
from calibre.ebooks.metadata.sources.base import Source, Option
from calibre.ebooks.chardet import xml_to_unicode
from calibre.utils.cleantext import clean_ascii_chars
from calibre import as_unicode
from lxml import etree
from lxml.html import fromstring
from collections import OrderedDict
from functools import partial
from Queue import Queue, Empty
from cbdb.worker import Worker #REPLACE from calibre_plugins.cbdb.worker import Worker
from devel import Devel #REPLACE from calibre_plugins.cbdb.devel import Devel
from metadata_compare import MetadataCompareKeyGen #REPLACE from calibre_plugins.cbdb.metadata_compare import MetadataCompareKeyGen

class Cbdb(Source):

    NAMESPACES={
        'x':"http://www.w3.org/1999/xhtml"
    }

    '''
    devel dir
    '''
    devel = Devel(r'\tmp\devel\cbdb', True)

    '''
    List of platforms this plugin works on For example: ['windows', 'osx', 'linux']
    '''
    supported_platforms = ['windows', 'osx', 'linux']

    BASE_URL = 'http://www.cbdb.cz/'

    '''
    The name of this plugin. You must set it something other than Trivial Plugin for it to work.
    '''
    name = 'cbdb'

    '''
    The version of this plugin as a 3-tuple (major, minor, revision)
    '''
    version = (1, 0, 0)

    '''
    A short string describing what this plugin does
    '''
    description = u'Download metadata and cover from cbdb.cz'

    '''
    The author of this plugin
    '''
    author = u'MarDuke marduke@centrum.cz'

    '''
    When more than one plugin exists for a filetype, the plugins are run in order of decreasing priority i.e. plugins with higher priority will be run first. The highest possible priority is sys.maxint. Default priority is 1.
    '''
    priority = 1

    '''
    The earliest version of calibre this plugin requires
    '''
    minimum_calibre_version = (1, 0, 0)

    '''
    If False, the user will not be able to disable this plugin. Use with care.
    '''
    can_be_disabled = True

    '''
    Set of capabilities supported by this plugin. Useful capabilities are: ‘identify’, ‘cover’
    '''
    capabilities = frozenset(['identify', 'cover'])

    '''
    List of metadata fields that can potentially be download by this plugin during the identify phase
    '''
    touched_fields = frozenset(['title', 'authors', 'tags', 'pubdate', 'comments', 'publisher', 'identifier:isbn', 'rating', 'identifier:cbdb', 'languages'])

    '''
    Set this to True if your plugin returns HTML formatted comments
    '''
    has_html_comments = False

    '''
    Setting this to True means that the browser object will add Accept-Encoding: gzip to all requests.
    This can speedup downloads but make sure that the source actually supports gzip transfer encoding correctly first
    '''
    supports_gzip_transfer_encoding = False

    '''
    Cached cover URLs can sometimes be unreliable (i.e. the download could fail or the returned image could be bogus.
    If that is often the case with this source set to False
    '''
    cached_cover_url_is_reliable = True

    '''
    A list of Option objects. They will be used to automatically construct the configuration widget for this plugin
    '''
    options = (Option('max_covers', 'number', 5, _('Maximum number of covers to get'),
                      _('The maximum number of covers to process from the google search result')),
               Option('size', 'choices', 'svga', _('Cover size'),
                      _('Search for covers larger than the specified size'),
                      choices=OrderedDict((
                          ('any', _('Any size'),),
                          ('l', _('Large'),),
                          ('qsvga', _('Larger than %s')%'400x300',),
                          ('vga', _('Larger than %s')%'640x480',),
                          ('svga', _('Larger than %s')%'600x800',),
                          ('xga', _('Larger than %s')%'1024x768',),
                          ('2mp', _('Larger than %s')%'2 MP',),
                          ('4mp', _('Larger than %s')%'4 MP',),
                      ))),
    )

    '''
    A string that is displayed at the top of the config widget for this plugin
    '''
    config_help_message = None

    '''
    If True this source can return multiple covers for a given query
    '''
    can_get_multiple_covers = True

    '''
    If set to True covers downloaded by this plugin are automatically trimmed.
    '''
    auto_trim_covers = False

    def identify(self, log, result_queue, abort, title=None, authors=None, identifiers={}, timeout=30):
        '''
        Identify a book by its title/author/isbn/etc.
        If identifiers(s) are specified and no match is found and this metadata source does not store all related identifiers (for example, all ISBNs of a book), this method should retry with just the title and author (assuming they were specified).
        If this metadata source also provides covers, the URL to the cover should be cached so that a subsequent call to the get covers API with the same ISBN/special identifier does not need to get the cover URL again. Use the caching API for this.
        Every Metadata object put into result_queue by this method must have a source_relevance attribute that is an integer indicating the order in which the results were returned by the metadata source for this query. This integer will be used by compare_identify_results(). If the order is unimportant, set it to zero for every result.
        Make sure that any cover/isbn mapping information is cached before the Metadata object is put into result_queue.
        Parameters:
            log – A log object, use it to output debugging information/errors
            result_queue – A result Queue, results should be put into it. Each result is a Metadata object
            abort – If abort.is_set() returns True, abort further processing and return as soon as possible
            title – The title of the book, can be None
            authors – A list of authors of the book, can be None
            identifiers – A dictionary of other identifiers, most commonly {‘isbn’:‘1234...’}
            timeout – Timeout in seconds, no network request should hang for longer than timeout.
        Returns:
            None if no errors occurred, otherwise a unicode representation of the error suitable for showing to the user
        '''

        self.devel.setLog(log)
        found = []
        xml = None
        detail_ident = None

        #test previous found first
        ident = identifiers.get(self.name, None)

        XPath = partial(etree.XPath, namespaces=self.NAMESPACES)
        entry = XPath('//x:div[@class="content_box_content"]/x:table[1]//x:a[starts-with(@href, "kniha-")]/@href')
        detail_test = XPath('//x:a[starts-with(@href, "seznam-oblibene-")]/@href')

        query = self.create_query(log, title=title, authors=authors,
                identifiers=identifiers)
        if not query:
            log.error('Insufficient metadata to construct query')
            return

        br = self.browser
        try:
            log.info('download page search %s'%query)
            raw = br.open(query, timeout=timeout).read().strip()
            raw = re.sub("ledna!</a></span>", b"ledna!</a>", raw)
        except Exception as e:
            log.exception('Failed to make identify query: %r'%query)
            return as_unicode(e)

        try:
            parser = etree.XMLParser(recover=True)
            clean = clean_ascii_chars(raw)

            self.devel.log_file('','search',  clean)

            feed = fromstring(clean, parser=parser)
            if len(parser.error_log) > 0: #some errors while parsing
                log.info('while parsing page occus some errors:')
                log.info(parser.error_log)

            entries = entry(feed)
            if len(entries) == 0:
                xml = feed
                detail_ident = detail_test(feed)[0].split("-")[-1]
                if ident is not None and detail_ident != ident:
                    found.append(ident)
            else:
                for book in entries:
                    if book != ident:
                        found.append(book)

        except Exception as e:
            log.exception('Failed to parse identify results')
            return as_unicode(e)

        if ident and found.count(ident) > 0:
            found.remove(ident)
            found.insert(0, ident)

        matches = len(found)
        if xml is not None:
            matches += 1

        log.info('Found %i matches'%matches)

        try:
            #if redirect push to worker actual parsed xml, no need to download and parse it again
            if xml is not None:
                workers = [Worker(detail_ident, result_queue, br, log, 0, self, xml, self.devel)]
            workers += [Worker(ident, result_queue, br, log, i, self, None, self.devel) for i, ident in enumerate(found)]

            for w in workers:
                w.start()
                time.sleep(0.1)

            while not abort.is_set():
                a_worker_is_alive = False
                for w in workers:
                    w.join(0.2)
                    if abort.is_set():
                        break
                    if w.is_alive():
                        a_worker_is_alive = True
                if not a_worker_is_alive:
                    break
        except Exception as e:
            log.error(e)

        return None

    def create_query(self,  log, title=None, authors=None, identifiers={}):
        '''
        create url for HTTP request
        '''
        from urllib import urlencode
        q = ''
        if title:
            q += ' '.join(self.get_title_tokens(title))

        if isinstance(q, unicode):
            q = q.encode('utf-8')
        if not q:
            return None
        return self.BASE_URL+'hledat.php?'+urlencode({
            'hledat':q
        })

    def get_cached_cover_url(self, identifiers):
        '''
        Return cached cover URL for the book identified by the identifiers dict or None if no such URL exists.
        Note that this method must only return validated URLs, i.e. not URLS that could result in a generic cover image or a not found error.
        '''
        url = None
        ident = identifiers.get(self.name, None)
        if ident is not None:
            url = self.cached_identifier_to_cover_url(ident)
        return url

    def download_cover(self, log, result_queue, abort, title=None, authors=None, identifiers={}, timeout=30, get_best_cover=False):
        '''
        Download a cover and put it into result_queue. The parameters all have the same meaning as for identify(). Put (self, cover_data) into result_queue.
        This method should use cached cover URLs for efficiency whenever possible. When cached data is not present, most plugins simply call identify and use its results.
        If the parameter get_best_cover is True and this plugin can get multiple covers, it should only get the “best” one.
        '''
        cached_urls = self.get_cached_cover_url(identifiers)
        if not title:
            return
        self.download_multiple_covers(title, authors, cached_urls, get_best_cover, timeout, result_queue, abort, log)

    def get_book_url(self, identifiers):
        '''
        Return a 3-tuple or None. The 3-tuple is of the form:
        (identifier_type, identifier_value, URL).
        The URL is the URL for the book identified by identifiers at this
        source. identifier_type, identifier_value specify the identifier
        corresponding to the URL.
        This URL must be browseable to by a human using a browser. It is meant
        to provide a clickable link for the user to easily visit the books page
        at this source.
        If no URL is found, return None. This method must be quick, and
        consistent, so only implement it if it is possible to construct the URL
        from a known scheme given identifiers.
        '''
        ident = identifiers.get(self.name, None)
        if ident:
            return (self.name, ident, self.BASE_URL + ident)
        else:
            return None

    def get_book_url_name(self, idtype, idval, url):
        '''
        Return a human readable name from the return value of get_book_url().
        '''
        return self.name

    def identify_results_keygen(self, title=None, authors=None, identifiers={}):
        '''
        Return a function that is used to generate a key that can sort Metadata
        objects by their relevance given a search query (title, authors,
        identifiers).

        These keys are used to sort the results of a call to :meth:`identify`.

        For details on the default algorithm see
        :class:`InternalMetadataCompareKeyGen`. Re-implement this function in
        your plugin if the default algorithm is not suitable.
        '''
        def keygen(mi):
            return MetadataCompareKeyGen(mi, self, title, authors,
                identifiers)
        return keygen

if __name__ == '__main__': # tests
    # To run these test setup calibre library (that inner which contains  calibre-debug)
    # and run run.bat
    from calibre.ebooks.metadata.sources.test import (test_identify_plugin,
            title_test, authors_test, series_test)
    test_identify_plugin(Cbdb.name,
        [
#             (
#                 {'identifiers':{'bookfan1': '83502'}, #basic
#                 'title': 'Čarovný svět Henry Kuttnera', 'authors':['Henry Kuttner']},
#                 [title_test('Čarovný svět Henry Kuttnera', exact=False)]
#             )
#            ,
#            (
#                {'identifiers':{'bookfan1': '83502'}, #edice
#                'title': 'Zlodějka knih', 'authors':['Markus Zusak']},
#                [title_test('Zlodějka knih', exact=False)]
#            )
#            ,
#             (
#                 {'identifiers':{'bookfan1': '83502'}, #serie
#                 'title': 'Hra o trůny', 'authors':['George Raymond Richard Martin']},
#                 [title_test('Hra o trůny', exact=False)]
#             )
#            ,
            (
                {'identifiers':{}, #short story
                'title': 'Meč osudu', 'authors':['Andrzej Sapkowski ']},
                [title_test('Meč osudu', exact=False)]
            )
#             ,
#             (
#                 {'identifiers':{}, #short story
#                 'title': 'Dilvermoon', 'authors':['Raymon Huebert Aldridge']},
#                 [title_test('Dilvermoon', exact=False)]
#             )
        ])