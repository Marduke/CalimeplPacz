#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import, print_function)

import inspect, traceback

__docformat__ = 'restructuredtext en'

class Log(object):

    DEBUG = 0
    INFO  = 1
    WARN  = 2
    ERROR = 3

    '''
    Parent log to which one is writing
    '''
    parent_log = None

    def __init__(self, name, parent_log):
        self.name = name
        self.parent_log = parent_log

    def exception(self, *args, **kwargs):
        limit = kwargs.pop('limit', None)
        self.__inner_log(self.ERROR, False, *args, **kwargs)
        self.__inner_log(self.DEBUG, True, traceback.format_exc(limit))

    def __call__(self, *args, **kwargs):
        self.__inner_log(self.INFO, False, *args, **kwargs)

    def __inner_log(self, level, pure, *args, **kwargs):
        if pure:
            self.parent_log.prints(level, *args, **kwargs)
        else:
            frame = inspect.getouterframes(inspect.currentframe(), 2)[2]
            prefix = '%s.%s(%s): '%(self.name, frame[3],frame[2])
            self.parent_log.prints(level, prefix, *args, **kwargs)