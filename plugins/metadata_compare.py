#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import, print_function)

import re

__docformat__ = 'restructuredtext en'

# Comparing Metadata objects for relevance
words = ("the", "a", "an", "of", "and")
prefix_pat = re.compile(r'^(%s)\s+'%("|".join(words)))
trailing_paren_pat = re.compile(r'\(.*\)$')
whitespace_pat = re.compile(r'\s+')

def cleanup_title(s):
    if not s:
        s = _('Unknown')
    s = s.strip().lower()
    s = prefix_pat.sub(' ', s)
    s = trailing_paren_pat.sub('', s)
    s = whitespace_pat.sub(' ', s)
    return s.strip()

class MetadataCompareKeyGen(object):
    '''
    Generate a sort key for comparison of the relevance of Metadata objects,
    given a search query. This is used only to compare results from the same
    metadata source, not across different sources.

    The sort key ensures that an ascending order sort is a sort by order of
    decreasing relevance.

    The algorithm is:

        * Prefer results that have the same ISBN as specified in the query
        * Prefer results with a cached cover URL
        * Prefer results with all available fields filled in
        * Prefer results that are an exact title match to the query
        * Prefer results with longer comments (greater than 10% longer)
        * Use the relevance of the result as reported by the metadata source's search
           engine
    '''


    def __init__(self, mi, source_plugin, title, authors, identifiers):
        if not mi:
            self.base = (2,2,2,2,2)
            self.comments_len = 0
            self.extra = 0
            return

        isbn = 1 if mi.isbn and identifiers.get('isbn', None) is not None \
                and mi.isbn == identifiers.get('isbn', None) else 2

        all_fields = 1 if source_plugin.test_fields(mi) is None else 2

        cl_title = cleanup_title(title)
        cl_title_mi = cleanup_title(mi.title)
        exact_title = 1 if title and \
                cl_title == cl_title_mi else 2

        contains_title = 1 if title and \
                cl_title in cl_title_mi else 2

        has_cover = 2 if (not source_plugin.cached_cover_url_is_reliable or
                source_plugin.get_cached_cover_url(mi.identifiers) is None) else 1

        #changed againt original in Calibre
        #we need another ordering
        #self.base = (isbn, has_cover, all_fields, exact_title)
        self.base = (exact_title, isbn, contains_title, all_fields, has_cover)
        self.comments_len = len(mi.comments.strip() if mi.comments else '')
        self.extra = (getattr(mi, 'source_relevance', 0), )

    def __cmp__(self, other):
        result = cmp(self.base, other.base)
        if result == 0:
            # Now prefer results with the longer comments, within 10%
            cx, cy = self.comments_len, other.comments_len
            t = (cx + cy) / 20
            delta = cy - cx
            if abs(delta) > t:
                result = delta
            else:
                result = cmp(self.extra, other.extra)
        return result


class PreFilterMetadataCompare(object):
    '''
    Generate a sort key for comparison of the relevance of Metadata objects,
    given a search query. This is used only to compare results from the same
    metadata source, not across different sources.

    The sort key ensures that an ascending order sort is a sort by order of
    decreasing relevance.

    The algorithm is:

        * Prefer results that have the same ISBN as specified in the query
        * Prefer results with a cached cover URL
        * Prefer results with all available fields filled in
        * Prefer results that are an exact title match to the query
        * Prefer results with longer comments (greater than 10% longer)
        * Use the relevance of the result as reported by the metadata source's search
           engine
    '''

    def __init__(self, mi, source_plugin, title, authors, identifiers):
        if not mi:
#             print("WHUUUT?")
            self.base = (2,2,2,2,2)
            self.comments_len = 0
            self.extra = 0
            return

#         if mi.identifiers:
#             print(mi.identifiers.get('dbknih'))
#             self.ident = as_unicode(mi.identifiers.get('dbknih'))
#         else:
#             print('None')
#
#         print(mi.isbn)
#         print(identifiers)
        isbn = 1 if mi.isbn and identifiers.get('isbn', None) is not None \
                and mi.isbn == identifiers.get('isbn', None) else 2

        all_fields = 1 if source_plugin.test_fields(mi) is None else 2

        cl_title = cleanup_title(title)
        cl_title_mi = cleanup_title(mi.title)
        exact_title = 1 if title and \
                cl_title == cl_title_mi else 2

        contains_title = 1 if title and \
                cl_title in cl_title_mi else 2

        has_cover = 2 if (not source_plugin.cached_cover_url_is_reliable or
                source_plugin.get_cached_cover_url(mi.identifiers) is None) else 1

        #changed againt original in Calibre
        #we need another ordering
        #self.base = (isbn, has_cover, all_fields, exact_title)
        self.base = (exact_title, isbn, contains_title, all_fields, has_cover)
        self.comments_len = len(mi.comments.strip() if mi.comments else '')
        self.extra = (getattr(mi, 'source_relevance', 0), )

#         print('isbn - %s'%isbn)
#         print('all_fields - %s'%all_fields)
#         print('exact_title - %s'%exact_title)
#         print('has_cover - %s'%has_cover)
#         print('comments_len - %s'%self.comments_len)
#         print('exta - %s'%self.extra)

    def __cmp__(self, other):
        result = cmp(self.base, other.base)
#         if result == 1:
#             winner = self.ident
#         elif result == -1:
#             winner = other.ident
#         else:
#             winner = "None"
#         print('%s vs %s =>%s'%(self.ident, other.ident, winner))
#         print(result)
        if result == 0:
            # Now prefer results with the longer comments, within 10%
            cx, cy = self.comments_len, other.comments_len
            t = (cx + cy) / 20
            delta = cy - cx
            if abs(delta) > t:
                result = delta
            else:
                result = cmp(self.extra, other.extra)
        return result