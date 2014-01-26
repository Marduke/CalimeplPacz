#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import, print_function)

import inspect, sys, traceback
from UserString import MutableString

__docformat__ = 'restructuredtext en'

class Log(object):

    '''
    In buffered mode Log grabs
    '''
    buffer = None

    '''
    Parent log to which one is writing
    '''
    parent_log = None

    def __init__(self, name, parent_log, buffered = True):
        self.name = name
        self.parent_log = parent_log
        self.buffered = buffered
        if buffered == True:
            self.buffer = MutableString()

    def info(self, param):
        self.__inner_log(param, "info")

    def error(self, param):
        self.__inner_log(param, type="error")

    def exception(self, param):
        exc_type, exc_value, exc_traceback = sys.exc_info()
        i, j = (traceback.extract_tb(exc_traceback, 1))[0][0:2]
        k = (traceback.format_exception_only(exc_type, exc_value))[0]
        self.__inner_log('%son %s(%s)'%(k,i,j), type="exception")

    def parent_write(self, param, type):
        if isinstance(self.parent_log, Log):
            if self.parent_log.buffer is not None:
                self.parent_log.buffer += param
            else:
                self.parent_log.info(param)
        else:
            self.parent_log.info(param)

    def __inner_log(self, param, type):
        frame = inspect.getouterframes(inspect.currentframe(), 2)[2]
        text = '%s:%s(%s): %s - %s'%(self.name, frame[3],frame[2], type, param)
        if self.buffered:
            self.buffer += text + '\n'
        else:
            self.parent_write(text, type)

    def digg(self):
        if self.buffered:
            self.parent_write(self.buffer, "info")
            self.buffer = MutableString()
