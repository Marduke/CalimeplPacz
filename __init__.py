#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import, print_function)

__license__   = 'GPL v3'
__copyright__ = '2013, MarDuke <marduke@centrum.cz>'
__docformat__ = 'restructuredtext en'

from calibre.ebooks.metadata.sources.base import Source
from calibre import as_unicode
from lxml import etree
from calibre.ebooks.chardet import xml_to_unicode
from calibre.utils.cleantext import clean_ascii_chars
from functools import partial
import re

class Databaze_knih(Source):
    
    #List of platforms this plugin works on For example: ['windows', 'osx', 'linux']
    supported_platforms = ['windows', 'osx', 'linux']
  
    #The name of this plugin. You must set it something other than Trivial Plugin for it to work.
    name = 'databaze_knih'

    #The version of this plugin as a 3-tuple (major, minor, revision)
    version = (0,  0, 1)

    #A short string describing what this plugin does
    description = u'Download metadata and cover from Databazeknih.cz'
    
    #The author of this plugin
    author = u'MarDuke marduke@centrum.cz'

    #When more than one plugin exists for a filetype, the plugins are run in order of decreasing priority i.e. plugins with higher priority will be run first. The highest possible priority is sys.maxint. Default priority is 1.
    priority = 1

    #The earliest version of calibre this plugin requires
    minimum_calibre_version = (1, 0, 0)

    #If False, the user will not be able to disable this plugin. Use with care.
    can_be_disabled = True
    
    #Set of capabilities supported by this plugin. Useful capabilities are: ‘identify’, ‘cover’
    capabilities = frozenset(['identify', 'cover'])
    
    #List of metadata fields that can potentially be download by this plugin during the identify phase
    touched_fields = frozenset(['title', 'authors', 'tags', 'pubdate', 'comments', 'publisher', 'identifier:isbn', 'rating', 'identifier:google', 'languages'])
    
    #Set this to True if your plugin returns HTML formatted comments
    has_html_comments = False
    
    #Setting this to True means that the browser object will add Accept-Encoding: gzip to all requests. This can speedup downloads but make sure that the source actually supports gzip transfer encoding correctly first
    supports_gzip_transfer_encoding = False
    
    #Cached cover URLs can sometimes be unreliable (i.e. the download could fail or the returned image could be bogus. If that is often the case with this source set to False
    cached_cover_url_is_reliable = True
    
    #A list of Option objects. They will be used to automatically construct the configuration widget for this plugin
    options = ()
    
    #A string that is displayed at the top of the config widget for this plugin
    config_help_message = None
    
    #If True this source can return multiple covers for a given query
    can_get_multiple_covers = False
    
    #If set to True covers downloaded by this plugin are automatically trimmed.
    auto_trim_covers = False
    
    #Split a list of jobs into at most num groups, as evenly as possible
    def split_jobs(self,  jobs, num):
        return None
    
    #Return the first field from self.touched_fields that is null on the mi object
    def test_fields(self, mi): 
        return None

    #Call this method in your plugin’s identify method to normalize metadata before putting the Metadata object into result_queue. You can of course, use a custom algorithm suited to your metadata source.
    def clean_downloaded_metadata(self, mi): 
        return None

    #Return a 3-tuple or None. The 3-tuple is of the form: (identifier_type, identifier_value, URL). The URL is the URL for the book identified by identifiers at this source. identifier_type, identifier_value specify the identifier corresponding to the URL. This URL must be browseable to by a human using a browser. It is meant to provide a clickable link for the user to easily visit the books page at this source. If no URL is found, return None. This method must be quick, and consistent, so only implement it if it is possible to construct the URL from a known scheme given identifiers.
    def get_book_url(self,  identifiers): #from parent
        return None

    #Return a human readable name from the return value of get_book_url().
    def get_book_url_name(self, idtype, idval, url): 
        return None

    #Return cached cover URL for the book identified by the identifiers dict or None if no such URL exists.
    #Note that this method must only return validated URLs, i.e. not URLS that could result in a generic cover image or a not found error.
    def get_cached_cover_url(self,  identifiers): 
        return None


    #Return a function that is used to generate a key that can sort Metadata objects by their relevance given a search query (title, authors, identifiers).
    #These keys are used to sort the results of a call to identify().
    #For details on the default algorithm see InternalMetadataCompareKeyGen. Re-implement this function in your plugin if the default algorithm is not suitable.
    def identify_results_keygen(self, title=None, authors=None, identifiers={}): 
        return None

    #Identify a book by its title/author/isbn/etc.
    #If identifiers(s) are specified and no match is found and this metadata source does not store all related identifiers (for example, all ISBNs of a book), this method should retry with just the title and author (assuming they were specified).
    #If this metadata source also provides covers, the URL to the cover should be cached so that a subsequent call to the get covers API with the same ISBN/special identifier does not need to get the cover URL again. Use the caching API for this.
    #Every Metadata object put into result_queue by this method must have a source_relevance attribute that is an integer indicating the order in which the results were returned by the metadata source for this query. This integer will be used by compare_identify_results(). If the order is unimportant, set it to zero for every result.
    #Make sure that any cover/isbn mapping information is cached before the Metadata object is put into result_queue.
    #Parameters:	
    #    log – A log object, use it to output debugging information/errors
    #    result_queue – A result Queue, results should be put into it. Each result is a Metadata object
    #    abort – If abort.is_set() returns True, abort further processing and return as soon as possible
    #    title – The title of the book, can be None
    #    authors – A list of authors of the book, can be None
    #    identifiers – A dictionary of other identifiers, most commonly {‘isbn’:‘1234...’}
    #    timeout – Timeout in seconds, no network request should hang for longer than timeout.
    #Returns:	
    #    None if no errors occurred, otherwise a unicode representation of the error suitable for showing to the user
    def identify(self, log, result_queue, abort, title=None, authors=None, identifiers={}, timeout=30): 
    
        XPath = partial(etree.XPath,   namespaces={'x':"http://www.w3.org/1999/xhtml"})
        entry          = XPath('//x:p[@class="new_search"]/x:a[@type="book"][2]')

        query = self.create_query(log, title=title, authors=authors,
                identifiers=identifiers)
        if not query:
            log.error('Insufficient metadata to construct query')
            return
        log.info('Generated search URL %r'%query)
        br = self.browser
        try:
            raw = br.open(query, timeout=timeout).read().strip()
                
            def fixHtml(obj):
                return obj.group().replace('&','&amp;')
                
            raw = re.sub('&.{3}[^;]',  fixHtml,  raw)
            raw = raw.decode('utf-8', errors='replace')#.replace("&", "&amp;")
            
        except Exception as e:
            log.exception('Failed to make identify query: %r'%query)
            return as_unicode(e)
            
        try:
            parser = etree.XMLParser(recover=True)
#            clear = xml_to_unicode(clean_ascii_chars(raw), strip_encoding_pats=True)
#            feed = etree.fromstring(clear[0], parser=parser)
#            entries = feed.findall('.//html')
#            pprint.pprint(entries)
            #clean = xml_to_unicode(clean_ascii_chars(raw), strip_encoding_pats=True)
            clean = clean_ascii_chars(raw)
            
            logfile = open("D:\\dwnraw.html", "w")
            try:
                logfile.write(clean)
            finally:
                logfile.close()
            
            feed = etree.fromstring(clean,  parser=parser)
            if len(parser.error_log) > 0: #some errors while parsing
                log.info('while parsing page occus some errors:')
                log.info(parser.error_log)
            entries = entry(feed)

        except Exception as e:
            log.exception('Failed to parse identify results')
            return as_unicode(e)
        
        return None
    
    #create url for HTTP request
    def create_query(self,  log, title=None, authors=None, identifiers={}):
        from urllib import urlencode
        BASE_URL = 'http://www.databazeknih.cz/search?'
        q = ''
        if title:
            q += ' '.join(self.get_title_tokens(title))

        if isinstance(q, unicode):
            q = q.encode('utf-8')
        if not q:
            return None
        return BASE_URL+urlencode({
            'q':q
        })


    #Download a cover and put it into result_queue. The parameters all have the same meaning as for identify(). Put (self, cover_data) into result_queue.
    #This method should use cached cover URLs for efficiency whenever possible. When cached data is not present, most plugins simply call identify and use its results.
    #If the parameter get_best_cover is True and this plugin can get multiple covers, it should only get the “best” one.
    def download_cover(log, result_queue, abort, title=None, authors=None, identifiers={}, timeout=30, get_best_cover=False): 
        return None

def dump(var,  indent = 0):
    ind = ''
    for _ in range(indent):
        ind += '\t'
    ind = '\n' + ind
    
    val = ''
    
    if type(var) is int:
        val += 'int %d'%var
    if type(var) is str:
        val += 'str %s'%var
    if type(var) is tuple:
        ind += '\t'
        val += '(tuple len=%d%svalue=%s'%(len(var), ind, ind)
        for x in var:
            val += dump(x,  indent + 2)
            val += '%s'%ind
        val += ')'
    return val

if __name__ == '__main__': # tests
    # To run these test use:
    # calibre-debug -e __init__.py
    from calibre.ebooks.metadata.sources.test import (test_identify_plugin,
            title_test, authors_test, series_test)
    test_identify_plugin(Databaze_knih.name,
        [
             (               
                {'identifiers':{'bookfan1': '83502'}, #serie
                'title': 'Čarovný svět Henry Kuttnera', 'authors':['Henry Kuttner']},
                [title_test('Čarovný svět Henry Kuttnera', exact=False)]
             )
        ])


