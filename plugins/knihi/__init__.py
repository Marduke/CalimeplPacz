#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import, print_function)
from html5lib.treebuilders import etree_lxml

__license__   = 'GPL v3'
__copyright__ = '2014, MarDuke <marduke@centrum.cz>'
__docformat__ = 'restructuredtext en'

import re, time, sys
from calibre.ebooks.metadata.sources.base import Source, Option
from calibre.ebooks.chardet import xml_to_unicode
from calibre.utils.cleantext import clean_ascii_chars
from calibre import as_unicode
from lxml import etree
from lxml.html import fromstring
from collections import OrderedDict
from functools import partial
from Queue import Queue, Empty
from knihi.worker import Worker #REPLACE from calibre_plugins.knihi.worker import Worker
from metadata_compare import MetadataCompareKeyGen #REPLACE from calibre_plugins.knihi.metadata_compare import MetadataCompareKeyGen
from pre_filter_compare import PreFilterMetadataCompare #REPLACE from calibre_plugins.knihi.pre_filter_compare import PreFilterMetadataCompare
from knihi.search_worker import SearchWorker #REPLACE from calibre_plugins.knihi.search_worker import SearchWorker
from log import Log #REPLACE from calibre_plugins.knihi.log import Log

class Knihi(Source):

    NAMESPACES={
        'x':"http://www.w3.org/1999/xhtml"
    }

    '''
    List of platforms this plugin works on For example: ['windows', 'osx', 'linux']
    '''
    supported_platforms = ['windows', 'osx', 'linux']

    BASE_URL = 'http://www.knihi.cz/'

    '''
    The name of this plugin. You must set it something other than Trivial Plugin for it to work.
    '''
    name = 'knihi'

    '''
    The version of this plugin as a 3-tuple (major, minor, revision)
    '''
    version = (1, 0, 0)

    '''
    A short string describing what this plugin does
    '''
    description = u'Download metadata and cover from knihi.cz'

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
    capabilities = frozenset(['identify'])

    '''
    List of metadata fields that can potentially be download by this plugin during the identify phase
    '''
    touched_fields = frozenset(['title', 'authors', 'tags', 'comments', 'identifier:knihi', 'languages'])

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
    options = (
               Option('max_search', 'number', 25,
                      'Maximum knih',
                      'Maximum knih které se budou zkoumat jestli vyhovují hledaným parametrům'),
    )

    '''
    A string that is displayed at the top of the config widget for this plugin
    '''
    config_help_message = None

    '''
    If True this source can return multiple covers for a given query
    '''
    can_get_multiple_covers = False

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

        self.log = Log(self.name, log)
        found = []

        #test previous found first
        ident = identifiers.get(self.name, None)
        XPath = partial(etree.XPath, namespaces=self.NAMESPACES)
        pages_count = XPath('//div[@id="strankovani"]/a[last()]/text()')

        query = self.create_query(title=title)
        if not query:
            self.log('Insufficient metadata to construct query')
            return

        br = self.browser
        try:
            self.log('download page search %s'%query)
            raw = br.open(query, timeout=timeout).read().strip()
        except Exception as e:
            self.log.exception('Failed to make identify query: %r'%query)
            return as_unicode(e)

        try:
            parser = etree.HTMLParser()
            clean = clean_ascii_chars(raw)
            feed = fromstring(clean, parser=parser)
            self.log.filelog(clean)

            more_pages = pages_count(feed)
            #more pages with search results
            que = Queue()
            if ident is not None:
                que.put(["-%s"%ident, title, authors])
            if len(more_pages) > 0:
                page_max = int(more_pages[0])
            else:
                page_max = 1

            sworkers = []
            sworkers.append(SearchWorker(que, self, timeout, log, 1, ident, feed, title))
            sworkers.extend([SearchWorker(que, self, timeout, log, (i + 1), ident, None, title) for i in range(1,page_max)])

            for w in sworkers:
                w.start()
                time.sleep(0.1)

            while not abort.is_set():
                a_worker_is_alive = False
                for w in sworkers:
                    w.join(0.2)
                    if abort.is_set():
                        break
                    if w.is_alive():
                        a_worker_is_alive = True
                if not a_worker_is_alive:
                    break

            act_authors = []
            for act in authors:
                act_authors.append(act.split(" ")[-1])

            tmp_entries = []
            while True:
                try:
                    tmp_entries.append(que.get_nowait())
                except Empty:
                    break

            self.log('Found %i matches'%len(tmp_entries))

            if len(tmp_entries) > self.prefs['max_search']:
                tmp_entries.sort(key=self.prefilter_compare_gen(title=title, authors=act_authors))
                tmp_entries = tmp_entries[:self.prefs['max_search']]

            for val in tmp_entries:
                found.append(val[0])
#TODO: all plugins - log found and fitlered into 2 log messages
#TODO: all plugins - if ident specified, search should use it as first result
            self.log('Filtred to %i matches'%len(found))

        except Exception as e:
            self.log.exception('Failed to parse identify results')
            return as_unicode(e)

        if ident and found.count(ident) > 0:
            found.remove(ident)
            found.insert(0, ident)

        try:
            workers = [Worker(ident, result_queue, br, log, i, self, None) for i, ident in enumerate(found)]

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
            self.log.exception(e)

        return None

    def create_query(self, title=None, number=1):
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
        return self.BASE_URL+'search.php?'+urlencode({
            'q':q,
            'zacatek':(number - 1)*10
        })

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
            return (self.name, ident, "%skniha-%s"%(self.BASE_URL,ident))
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

    def prefilter_compare_gen(self, title=None, authors=None):
        '''
        Return a function that used to preOrdering if ser get more results
        than we want to check. Filtering should found most relevant results
        based on title and authors
        '''
        def keygen(data):
            return PreFilterMetadataCompare(data, self, title, authors)
        return keygen

if __name__ == '__main__': # tests
    # To run these test setup calibre library (that inner which contains  calibre-debug)
    # and run run.bat
    from calibre.ebooks.metadata.sources.test import (test_identify_plugin,
            title_test, authors_test, series_test)
    test_identify_plugin(Knihi.name,
        [
            (
                {'identifiers':{}, #serie
                 'title': 'Tanec s carevnou', 'authors':['Petra Neomillnerová']},
                [title_test('Tanec s carevnou', exact=False)]
            )
#             ,
#             (
#                 {'identifiers':{}, #tags
#                  'title': '3x soukromý detektiv Lew Archer', 'authors':['Ross Macdonald']},
#                 [title_test('3x soukromý detektiv Lew Archer', exact=False)]
#             )
#             ,
#             (
#                 {'identifiers':{}, #simple book
#                  'title': 'Duna', 'authors':['Frank Herbert']},
#                 [title_test('Duna', exact=False)]
#             )
        ])