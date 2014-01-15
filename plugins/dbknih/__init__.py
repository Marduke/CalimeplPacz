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
from calibre.ebooks.metadata.sources.base import Source
from calibre.ebooks.chardet import xml_to_unicode
from calibre.utils.cleantext import clean_ascii_chars
from calibre import as_unicode
from lxml import etree
from lxml.html import fromstring
from functools import partial
from Queue import Queue, Empty
from dbknih.worker import Worker #REPLACE from calibre_plugins.dbknih.worker import Worker
from devel import Devel #REPLACE from calibre_plugins.dbknih.devel import Devel

NAMESPACES={
    'x':"http://www.w3.org/1999/xhtml"
}

class Dbknih(Source):

    '''
    devel dir
    '''
    devel = Devel(r'D:\tmp\devel\dbknih', True)

    '''
    List of platforms this plugin works on For example: ['windows', 'osx', 'linux']
    '''
    supported_platforms = ['windows', 'osx', 'linux']

    BASE_URL = 'http://www.databazeknih.cz/'

    '''
    The name of this plugin. You must set it something other than Trivial Plugin for it to work.
    '''
    name = 'dbknih'

    '''
    The version of this plugin as a 3-tuple (major, minor, revision)
    '''
    version = (1, 0, 0)

    '''
    A short string describing what this plugin does
    '''
    description = u'Download metadata and cover from Databazeknih.cz'

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
    touched_fields = frozenset(['title', 'authors', 'tags', 'pubdate', 'comments', 'publisher', 'identifier:isbn', 'rating', 'identifier:dbknih', 'languages'])

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
    options = ()

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
    def identify(self, log, result_queue, abort, title=None, authors=None, identifiers={}, timeout=30):

        self.devel.setLog(log)
        found = []

        #test previous found first
        ident = identifiers.get(self.name, None)
        if ident:
            if ident.startswith('knihy/') or ident.startswith('povidky/'):
                found.append(ident)

        XPath = partial(etree.XPath, namespaces=NAMESPACES)
        entry = XPath('//x:p[@class="new_search"]/x:a[@type="book"][2]/@href')
        story = XPath('//x:a[@class="search_to_stats" and @type="other"]/@href')

        query = self.create_query(log, title=title, authors=authors,
                identifiers=identifiers)
        if not query:
            log.error('Insufficient metadata to construct query')
            return

        br = self.browser
        try:
            log.info('download page search %s'%query)
            raw = br.open(query, timeout=timeout).read().strip()

            #following block fix html, some people dont use html escape on every &...
            def fixHtml(obj):
                return obj.group().replace('&','&amp;')

            raw = re.sub('&.{3}[^;]',  fixHtml,  raw)
            raw = raw.decode('utf-8', errors='replace')

        except Exception as e:
            log.exception('Failed to make identify query: %r'%query)
            return as_unicode(e)

        try:
            parser = etree.XMLParser(recover=True)
            clean = clean_ascii_chars(raw)

            self.devel.log_file('','search',  clean)

            feed = fromstring(clean,  parser=parser)
            if len(parser.error_log) > 0: #some errors while parsing
                log.info('while parsing page occus some errors:')
                log.info(parser.error_log)

            #Books
            found.extend(entry(feed))
            #Short stories
            found.extend(story(feed))
        except Exception as e:
            log.exception('Failed to parse identify results')
            return as_unicode(e)

        #remove duplicity
#         copy = found[:]
#         for value in set(copy):
#             found.remove(value)

        try:
            workers = [Worker(ident, result_queue, br, log, i, self, self.devel) for i, ident in enumerate(found)]

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

    '''
    create url for HTTP request
    '''
    def create_query(self,  log, title=None, authors=None, identifiers={}):
        from urllib import urlencode
        q = ''
        if title:
            q += ' '.join(self.get_title_tokens(title))

        if isinstance(q, unicode):
            q = q.encode('utf-8')
        if not q:
            return None
        return self.BASE_URL+'search?'+urlencode({
            'q':q
        })

    '''
    Return cached cover URL for the book identified by the identifiers dict or None if no such URL exists.
    Note that this method must only return validated URLs, i.e. not URLS that could result in a generic cover image or a not found error.
    '''
    def get_cached_cover_url(self, identifiers):
        url = None
        ident = identifiers.get(self.name, None)
        if ident is not None:
            url = self.cached_identifier_to_cover_url(ident)
        return url

    '''
    Download a cover and put it into result_queue. The parameters all have the same meaning as for identify(). Put (self, cover_data) into result_queue.
    This method should use cached cover URLs for efficiency whenever possible. When cached data is not present, most plugins simply call identify and use its results.
    If the parameter get_best_cover is True and this plugin can get multiple covers, it should only get the “best” one.
    '''
    def download_cover(self, log, result_queue, abort, title=None, authors=None, identifiers={}, timeout=30, get_best_cover=False):
        cached_url = self.get_cached_cover_url(identifiers)
        if cached_url is None:
            log.info('No cached cover found, running identify')
            rq = Queue()
            self.identify(log, rq, abort, title=title, authors=authors, identifiers=identifiers)
            if abort.is_set():
                return
            results = []
            while True:
                try:
                    results.append(rq.get_nowait())
                except Empty:
                    break
            results.sort(key=self.identify_results_keygen(
                title=title, authors=authors, identifiers=identifiers))
            for mi in results:
                cached_url = self.get_cached_cover_url(mi.identifiers)
                if cached_url is not None:
                    break
        if cached_url is None:
            log.info('No cover found')
            return

        if abort.is_set():
            return
        br = self.browser
        log('Downloading cover from:', cached_url)
        try:
            cdata = br.open_novisit(cached_url, timeout=timeout).read()
            result_queue.put((self, cdata))
        except:
            log.exception('Failed to download cover from:', cached_url)


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
    def get_book_url(self, identifiers):
        ident = identifiers.get(self.name, None)
        if ident:
            return (self.name, ident, self.BASE_URL + ident)
        else:
            return None

    '''
    Return a human readable name from the return value of get_book_url().
    '''
    def get_book_url_name(self, idtype, idval, url):
        return self.name

if __name__ == '__main__': # tests
    # To run these test setup calibre library (that inner which contains  calibre-debug)
    # and run run.bat
    from calibre.ebooks.metadata.sources.test import (test_identify_plugin,
            title_test, authors_test, series_test)
    test_identify_plugin(Dbknih.name,
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
                {'identifiers':{'bookfan1': '83502'}, #short story
                'title': 'Absolon', 'authors':['Henry Kuttner']},
                [title_test('Absolon', exact=False)]
            )
#             ,
#             (
#                 {'identifiers':{}, #short story
#                 'title': 'Dilvermoon', 'authors':['Raymon Huebert Aldridge']},
#                 [title_test('Dilvermoon', exact=False)]
#             )
        ])