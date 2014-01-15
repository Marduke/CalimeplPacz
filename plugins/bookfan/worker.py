#!/usr/bin/env python# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:aifrom __future__ import (unicode_literals, division, absolute_import,                        print_function)__license__   = 'GPL v3'__copyright__ = '2012, MarDuke <marduke@centrum.cz>'__docformat__ = 'restructuredtext en'import socket, re, datetime, math, stringfrom threading import Threadfrom lxml.html import fromstringfrom calibre.ebooks.metadata.book.base import Metadatafrom calibre.library.comments import sanitize_comments_htmlfrom calibre.utils.cleantext import clean_ascii_charsfrom calibre.utils.icu import lowerclass Worker(Thread): # Get details    '''    Get book details from Webscription book page in a separate thread    '''    def __init__(self, url, match_authors, result_queue, browser, log, relevance, plugin, timeout=20):        Thread.__init__(self)        self.daemon = True        self.url, self.result_queue = url,  result_queue        self.match_authors = match_authors        self.log, self.timeout = log, timeout        self.relevance, self.plugin = relevance, plugin        self.browser = browser.clone_browser()        self.cover_url = self.bookfan_id = self.isbn = None    def run(self):        try:            self.get_details()        except:            self.log.exception('get_details failed for url: %r'%self.url)    def get_details(self):        try:            self.log.info('BookFan url: %r'%self.url)            raw = self.browser.open_novisit(self.url, timeout=self.timeout).read().strip()        except Exception as e:            if callable(getattr(e, 'getcode', None)) and \                    e.getcode() == 404:                self.log.error('URL malformed: %r'%self.url)                return            attr = getattr(e, 'args', [None])            attr = attr if attr else [None]            if isinstance(attr[0], socket.timeout):                msg = 'BookFan timed out. Try again later.'                self.log.error(msg)            else:                msg = 'Failed to make details query: %r'%self.url                self.log.exception(msg)            return        raw = raw.decode('utf-8', errors='replace')        #open('E:\\t3.html', 'wb').write(raw)        if '<title>404 - ' in raw:            self.log.error('URL malformed: %r'%self.url)            return        try:            root = fromstring(clean_ascii_chars(raw))        except:            msg = 'Failed to parse BookFan details page: %r'%self.url            self.log.exception(msg)            return        self.parse_details(root)    def parse_details(self, root):        isbn = publisher = year = None        try:            bookfan_id = self.parse_id(self.url)        except:            self.log.exception('Error parsing BookFan id for url: %r'%self.url)            bookfan_id = None        try:            title = self.parse_title(root)        except:            self.log.exception('Error parsing title for url: %r'%self.url)            title = None        try:            authors = self.parse_authors(root)        except:            self.log.exception('Error parsing authors for url: %r'%self.url)            authors = []        if not title or not authors or not bookfan_id:            self.log.error('Could not find title/authors/BookFan id for %r'%self.url)            self.log.error('BookFan: %r Title: %r Authors: %r'%(bookfan_id, title,                authors))            return        self.bookfan_id = bookfan_id        rating = comments = series = series_index = None        try:            rating = self.parse_rating(root)        except:            self.log.exception('Error parsing ratings for url: %r'%self.url)        try:            comments = self.parse_comments(root)        except:            self.log.exception('Error parsing comments for url: %r'%self.url)        try:            (series,series_index) = self.parse_series(root)        except:            self.log.info('Series not found.')        try:            tags = self.parse_tags(root)        except:            self.log.exception('Error parsing tags for url: %r'%self.url)            tags = None        if bookfan_id:            editions = self.get_editions()            try:                self.cover_url = self.parse_cover(root)            except:                self.log.exception('Error parsing cover for url: %r'%self.url)            if editions:                num_editions = len(editions)                self.log.info('Nalezeno %d vydani'%num_editions)                for edition in editions:                    (year, cover_url, publisher, isbn) = edition                    mi = Metadata(title, authors)                    self.bookfan_id = "%s#%s"%(bookfan_id,year)                    mi.set_identifier('bookfan', self.bookfan_id)                    mi.source_relevance = self.relevance                    mi.rating = rating                    mi.comments = comments                    mi.series = series                    mi.series_index = series_index                    if self.cover_url:                        mi.cover_url = self.cover_url                        self.plugin.cache_identifier_to_cover_url(self.bookfan_id, self.cover_url)                    if tags:                        mi.tags = tags                    mi.has_cover = bool(self.cover_url)                    if publisher:                        mi.publisher = publisher                    mi.isbn = isbn                    mi.pubdate = self.prepare_date(int(year))                    mi.language = "ces"                    self.result_queue.put(mi)            else:                mi = Metadata(title, authors)                mi.set_identifier('bookfan', self.bookfan_id)                mi.source_relevance = self.relevance                mi.rating = rating                mi.comments = comments                mi.series = series                mi.series_index = series_index                mi.cover_url = self.cover_url                if tags:                    mi.tags = tags                mi.has_cover = bool(self.cover_url)                mi.publisher = publisher                mi.isbn = isbn                if year != None:                    mi.pubdate = self.prepare_date(int(year))                mi.language = "ces"                self.result_queue.put(mi)                if self.bookfan_id:                    if self.cover_url:                        self.plugin.cache_identifier_to_cover_url(self.bookfan_id, self.cover_url)    def parse_id(self, url):        return re.search('/kniha/(\d+)', url).groups(0)[0]    def parse_title(self, root):        title_node = root.xpath('//h1[@itemprop="name"]')        if title_node:            self.log.info('Title: %s'%title_node[0].text.strip())            return title_node[0].text.strip()    def parse_authors(self, root):        authors = ''        author_nodes = root.xpath('//h2[@class="author"]/a')        if author_nodes:            authors = []            for author_node in author_nodes:                author = author_node.text.strip()                self.log.info('Autor: %s'%author)                authors.append(author)        else:            self.log.info('No author has been found')        def ismatch(authors):            authors = lower(' '.join(authors))            amatch = not self.match_authors            for a in self.match_authors:                if lower(a) in authors:                    amatch = True                    break            if not self.match_authors:                amatch = True            return amatch        if not self.match_authors or ismatch(authors):            return authors        self.log('Rejecting authors as not a close match: ', ','.join(authors))    def parse_comments(self, root):        description_nodes = root.xpath('//p[@id="book-description-paragraph"]')        if description_nodes:            comments = []            for node in description_nodes:                node_text = node.text_content()                comments.append("<p>" + node_text + "</p>")            comments = sanitize_comments_html("".join(comments))            comments = comments.replace('Anotace: ', '')            return comments        else:            self.log.info('No comment node was found.')    def parse_cover(self, root):        cover_node = root.xpath('//a[@class="lightbox"]/@href')        if cover_node:            cover_url = cover_node[0]            return cover_url    def parse_rating(self, root):        rating_node = root.xpath('//span[@class="rating-box "]/@title')        if rating_node:            rating_string = rating_node[0]            match = re.search('(\d+)', rating_string)            if match:                rating_proc = match.groups(0)[0]                self.log.info('Rating: %i'%int(rating_proc))                rating_value = math.ceil(int(rating_proc) / 20)                return rating_value        else:            self.log.info('Rating node not found')    def parse_series(self, root):        series_node = root.xpath('//a[@class="series_name"]')        if series_node:            series_name = series_node[0].text_content()            series_index_nodes = root.xpath('//span[@class="active"]')            series_text = series_index_nodes[0].text_content()            match = re.search('#(\d+)',series_text)            if match:                self.log.info('Found Serie %s'%series_name)                return (series_name, int(match.groups(0)[0]))            else:                self.log.info('Series: %s, Index not found'%series_name)                return (series_name, None)        else:            self.log.info('Series node not found')        return (None, None)    def parse_tags(self,root):        tags = []        tags_tmp = []        tags_nodes = root.xpath('//meta[@property="book:tag"]/@content')        if tags_nodes:            tags_tmp = string.split(tags_nodes[0], ', ')        tags_nodes = root.xpath('//a[@class="genre"]')        if tags_nodes:            tags_tmp.append(tags_nodes[0].text_content())        for tag in tags_tmp:            tags.append(tag.lower())        return sorted(set(tags))    def get_editions(self):        url_parts = self.url.split('#')        if len(url_parts) == 2:            base_url,edition_year = url_parts        else:            base_url = url_parts[0]            edition_year = None        url = '%s/vydani'%(base_url)        try:            self.log.info('BookFan url: %r'%url)            raw = self.browser.open_novisit(url, timeout=self.timeout).read().strip()        except Exception as e:            if callable(getattr(e, 'getcode', None)) and \                    e.getcode() == 404:                self.log.error('URL malformed: %r'%url)                return            attr = getattr(e, 'args', [None])            attr = attr if attr else [None]            if isinstance(attr[0], socket.timeout):                msg = 'BookFan timed out. Try again later.'                self.log.error(msg)            else:                msg = 'Failed to make details query: %r'%url                self.log.exception(msg)            return        raw = raw.decode('utf-8', errors='replace')        #open('E:\\t3.html', 'wb').write(raw)        if '<title>404 - ' in raw:            self.log.error('URL malformed: %r'%url)            return        try:            root = fromstring(clean_ascii_chars(raw))        except:            msg = 'Failed to parse BookFan details page: %r'%url            self.log.exception(msg)            return        self.log.info('Trying to parse editions')        try:            editions = self.parse_editions(root,edition_year)        except:            self.log.exception('Failed to parse editions page')            editions = []        return editions    def parse_editions(self, root, edition_year):        editions = []        edition_nodes = root.xpath('//div[@class="biblio"]/table/tbody/tr')        if edition_nodes:            isbn = publisher = year = ''            pushed = True            for node in edition_nodes:                children = node.xpath('*')                if not children:                    continue                match = re.search(u'knihy',children[0].text_content())                if match:                    if pushed == False:                        editions.append((year, None, publisher, isbn))                    pushed = False                    continue                match = re.search('ISBN',children[0].text_content())                if match:                    isbn = children[1].text_content()                    if isbn == 'N/A':                        isbn = None                    continue                match = re.search('Rok',children[0].text_content())                if match:                    year = children[1].text_content()                    continue                match = re.search('Vydavatel',children[0].text_content())                if match:                    publisher = children[1].text_content()                    continue            if pushed == False:                editions.append((year, None, publisher, isbn))        else:            self.log.info("No edition nodes")        return editions    def prepare_date(self,year):        from calibre.utils.date import utc_tz        return datetime.datetime(year, 1, 1, tzinfo=utc_tz)