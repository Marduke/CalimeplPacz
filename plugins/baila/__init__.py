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
from baila.worker import Worker #REPLACE from calibre_plugins.baila.worker import Worker
from metadata_compare import MetadataCompareKeyGen #REPLACE from calibre_plugins.baila.metadata_compare import MetadataCompareKeyGen
from pre_filter_compare import PreFilterMetadataCompare #REPLACE from calibre_plugins.baila.pre_filter_compare import PreFilterMetadataCompare
from baila.search_worker import SearchWorker #REPLACE from calibre_plugins.baila.search_worker import SearchWorker
from log import Log #REPLACE from calibre_plugins.baila.log import Log

class Baila(Source):

    NAMESPACES={
        'x':"http://www.w3.org/1999/xhtml"
    }

    '''
    List of platforms this plugin works on For example: ['windows', 'osx', 'linux']
    '''
    supported_platforms = ['windows', 'osx', 'linux']

    BASE_URL = 'http://baila.net/'

    '''
    The name of this plugin. You must set it something other than Trivial Plugin for it to work.
    '''
    name = 'baila'

    '''
    The version of this plugin as a 3-tuple (major, minor, revision)
    '''
    version = (1, 0, 0)

    '''
    A short string describing what this plugin does
    '''
    description = u'Download metadata and cover from baila.net'

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
    touched_fields = frozenset(['title', 'authors', 'tags', 'pubdate', 'comments', 'publisher', 'identifier:isbn', 'identifier:baila', 'languages'])

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
        xml = None

        #test previous found first
        ident = identifiers.get(self.name, None)
#TODO: search workers
        XPath = partial(etree.XPath, namespaces=self.NAMESPACES)
        list = XPath('//div[@class="works paging-container scrollable"]/div[@id]/div[@class="book-info"]')
        result_count = XPath('//div[@id="works"]/h2[@class="title"]/span[@class="n_found"]/text()')
        detail_text = XPath('//div[@class="book content"]/@id')

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
            parser = etree.XMLParser(recover=True)
            clean = clean_ascii_chars(raw)
            feed = fromstring(clean, parser=parser)

            detail = detail_text(feed)
            if len(detail) > 0:
                xml = feed
                detail_ident = detail[0].split("_")[1]
                found.append(detail_ident)
            else:
                self.log("more")
                more_pages = result_count(feed)
                #more pages with search results
                que = Queue()
                if ident is not None:
                    que.put(["-%s"%ident, title, authors])
                results = int(re.compile("\d+").findall(more_pages[0])[0])
                self.log(results)
                page_max = int(results / 10)
                if results % 10 > 0:
                    page_max += 1

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

                if len(tmp_entries) > self.prefs['max_search']:
                    tmp_entries.sort(key=self.prefilter_compare_gen(title=title, authors=act_authors))
                    tmp_entries = tmp_entries[:self.prefs['max_search']]

                for val in tmp_entries:
                    found.append(val[0])

            self.log('Found %i matches'%len(found))

        except Exception as e:
            self.log.exception('Failed to parse identify results')
            return as_unicode(e)

        if ident and found.count(ident) > 0:
            found.remove(ident)
            found.insert(0, ident)

        try:
            if xml is not None:
                workers = [Worker(detail_ident, result_queue, br, log, 0, self, xml)]
            else:
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
        if number == 1:
            return self.BASE_URL+'search?'+urlencode({
                'search':q
            })
        else:
            return self.BASE_URL+'search?'+urlencode({
                'search':q,
                'page_w':number
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
        self.log = Log(self.name, log)
        cached_url = self.get_cached_cover_url(identifiers)
        if cached_url is None:
            self.log('No cached cover found, running identify')
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
        self.log('Downloading cover from:%s'%cached_url)
        try:
            cdata = br.open_novisit(cached_url, timeout=timeout).read()
            result_queue.put((self, cdata))
        except:
            self.log.exception('Failed to download cover from:', cached_url)

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
    test_identify_plugin(Baila.name,
        [
            (
                {'identifiers':{},
#                 'test-cases':{
#                     'type': 'long_search',
#                     'title':'Vlk',
#                     'authors': ['E. E Knight'],
#                     'serie': 'Země upírů',
#                     'serie_index': 1,
#                     'tags': ['americká literatura','sci-fi','vědeckofantastické romány'],
#                     'publisher': 'Triton / Trifid',
#                     'pubdate': '2008-01-01T00:00:00',
#                     'comments': 'Louisiana, druhá polovina 21. století: Země má nové šéfy Karany, mimozemšťany, kteří k nám pronikli mezihvězdnou bránou mezi světy. Už tady jednou byli, zůstaly po nich legendy o upírech a vlkodlacích. Tentokrát se na invazi důkladně připravili. Karané jsou staré nesmrtelné plémě, protože vysávají „vitální auru“ živých tvorů. Čím inteligentnější tvor, tím výživnější aura. Lidská aura je velice výživná. Karané rozvrátili lidskou společnost sérií globálních katastrof, upravili klima a nastolili Karské zřízení. Od lidí nechtějí mnoho – pouze jejich životy.',
#                     'identifiers': {'isbn':'9788073871499', 'baila':'/kniha/129544996'},
#                     'covers': ['http://baila.net/img/ebda30c55c4ef20d'],
#                 },
                 'title': 'Vlk', 'authors':['E. E Knight']},
                [title_test('Vlk', exact=False)]
            )
            ,
            (
                {'identifiers':{},
#                  'test-cases':{
#                     'type': 'redirect search',
#                     'title':'Bestie uvnitř',
#                     'authors': ['Lotte Hammer', 'Søren Hammer'],
#                     'serie': None,
#                     'serie_index': None,
#                     'tags': ['detektivky, napětí','detektivní romány','dánské romány'],
#                     'publisher': 'Host',
#                     'pubdate': '2012-01-01T00:00:00',
#                     'comments': '''Jednoho rána vběhnou děti do školní tělocvičny a spatří něco hrozného: ze stropu tam visí pět nahých znetvořených mužských těl. Na místo je okamžitě povolán vrchní kriminální komisař Konrad Simonsen se svým týmem z kodaňského oddělení vražd. Výslechy školního personálu brzy odhalí prvního podezřelého: školníka Pera Clausena. Ten sice na první pohled nevypadá jako bestiální vrah, ale od začátku je patrné, že ví víc, než prozradil policii.<br/>
# Policejní pátrání dlouho nepřináší odpovědi na základní otázky: Co bylo motivem? A proč byla vražda pěti mužů pečlivě naaranžována jako hromadná poprava? Je pachatel jen jeden, nebo má vraždy na svědomí organizovaná skupina?<br/>
# Dříve než od policie získává dánská veřejnost informace z rafinované kampaně v tisku a celý případ se rázem jeví ve zcela jiné perspektivě. Je možné, aby vrah byl zároveň obětí? A kdo bude nakonec rozhodovat o vině a nevině – média, veřejné mínění, nebo Konrad Simonsen a jeho vyšetřovací tým?''',
#                     'identifiers': {'isbn':'9788072945825', 'baila':'54625789'},
#                     'covers': ['http://baila.net/img/6b8e24c64b98f84f'],
#                 },
                 'title': 'Bestie uvnitř', 'authors':['Soren Hammer','Lotte Hammerová']},
                [title_test('Bestie uvnitř', exact=False)]
            )
            ,
            (
                {'identifiers':{},
#                  'test-cases':{
#                     'type': 'simple book',
#                     'title':'Duna',
#                     'authors': ['Frank Herbert'],
#                     'serie': None,
#                     'serie_index': None,
#                     'tags': ['americká literatura','americké romány','romány','sci-fi','vědecko-fantastické romány'],
#                     'publisher': 'Baronet',
#                     'pubdate': '2006-01-01T00:00:00',
#                     'comments': '''Kultovní SF sága Duny, kterou mnozí znají z některé její filmové adaptace, se rodila nesnadno. Její první díl, román Duna, který později proslavil jednoho z dnes již klasiků SF literatury, Franka Herberta, vyšel v roce 1963 v časopise Analog pod názvem Svět Duny, ovšem jen jeho část. Díky obrovskému ohlasu u čtenářů napsal vzápětí autor pokračování příběhu Prorok Duny. Pro knižní vydání (1965) obě části spojil a výstižně a stručně nazval Duna. Úspěch románu o pouštní planetě Arrakis a jejím pokladu stále rostl, hned v následujícím roce (1966) získal jak cenu Nebula, tak Hugo.''',
#                     'identifiers': {'isbn':'8072149415', 'baila':'45272936'},
#                     'covers': ['http://baila.net/img/b1ba9c851b493b8f'],
#                 }
                 'title': 'Duna', 'authors':['Frank Herbert']},
                [title_test('Duna', exact=False)]
            )
        ])