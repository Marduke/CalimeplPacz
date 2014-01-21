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

class PreFilterMetadataCompare(object):
    '''
    Generate key that is used to sort book peak in search to remove
    book that cant be what we looking for to increase quality of search
    and decrease time of search
    '''

    def __init__(self, data, plugin, title, authors):
        if not data:
#             print("WHUUUT?")
            self.base = (0,0,0)
            return

        cl_title = cleanup_title(title)
        cl_title_data = cleanup_title(data[1])

        exact_title = 1 if title and \
                cl_title == cl_title_data else 0

        title_segments = list(set(cl_title.split(" ")) & set(cl_title_data.split(" ")))
        author_segments = list(set(data[2]) & set(authors)) #authors surname list compare

        self.base = (exact_title, title_segments, author_segments)

    def __cmp__(self, other):
        result = cmp(self.base, other.base)
        return -result
