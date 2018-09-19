#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2018 Ryan Mackenzie White <ryan.white4@canada.ca>
#
# Distributed under terms of the  license.

"""
Testing algorithms
"""
import sys
import logging
from pprint import pformat

from artemis.core.algo import AlgoBase


class DummyAlgo1(AlgoBase):
   
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        self.__logger.debug(pformat(self.__dict__))
        self.__logger.info('%s: __init__ DummyAlgo1' % self.name)
    
    def initialize(self):
        self.__logger.info(self.__logger)
        self.__logger.info(self._DummyAlgo1__logger)
        self.__logger.info('%s: property %s' % (self.name, self.properties.myproperty))
        self.__logger.info('%s: Initialized DummyAlgo1' % self.name)

    def book(self):
        pass

    def execute(self, payload):
        if(logging.getLogger().isEnabledFor(logging.DEBUG) or
                self.__logger.isEnabledFor(logging.DEBUG)):

            # Prevent excessive formating calls when not required
            # Note that we can indepdently change the logging level 
            # for algo loggers and root logger
            # Use string interpolation to prevent excessive format calls
            self.__logger.debug('%s: execute ' % self.name)
            # Check logging level if formatting requiered
            self.__logger.debug('{}: execute: payload {}'.format(self.name, sys.getsizeof(payload)))
        
        self.__logger.debug("Trying to debug")

    def finalize(self):
        pass

