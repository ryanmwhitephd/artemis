#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2018 Ryan Mackenzie White <ryan.white4@canada.ca>
#
# Distributed under terms of the  license.

"""
Algorithm which configures a reader
given a bytes object
"""
from ast import literal_eval
import csv
import io
from statistics import mean

import pyarrow as pa
from pyarrow.csv import read_csv, ReadOptions

from artemis.core.algo import AlgoBase
from artemis.io.reader import Reader
from artemis.core.properties import JobProperties
from artemis.decorators import timethis
from artemis.core.physt_wrapper import Physt_Wrapper
from artemis.utils.utils import range_positive


class CsvParserAlgo(AlgoBase):

    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        self.__logger.info('%s: __init__ CsvParserAlgo' % self.name)
        self.__logger.debug('%s: __init__ CsvParserAlgo' % self.name)
        self.__logger.warning('%s: __init__ CsvParserAlgo' % self.name)
        self.reader = None
        self.jobops = None

    def initialize(self):
        self.__logger.info(self.__logger)
        self.__logger.info(self._CsvParserAlgo__logger)
        self.reader = Reader()
        self.jobops = JobProperties()
        self.__logger.info('%s: Initialized CsvParserAlgo' % self.name)

    def book(self):
        self.__logger.info("Book")
        self.hbook = Physt_Wrapper()
        self.__timers = dict()
        self.__timers['pyparse'] = list()
        self.__timers['pyarrowparse'] = list()
        bins = [x for x in range_positive(0., 100., 2.)]
        self.hbook.book(self.name, 'time.pyparse', bins, 'ms')
        self.hbook.book(self.name, 'time.pyarrowparse', bins, 'ms')

    @timethis
    def py_parsing(self, schema, columns, length, block):
        try:
            with io.TextIOWrapper(io.BytesIO(block)) as file_:
                reader = csv.reader(file_)
                try:
                    next(reader)
                except Exception:
                    self.__logger.error("Cannot read inserted header")
                    raise
                try:
                    for row in reader:
                        # print(row)
                        length += 1
                        for i, item in enumerate(row):
                            if item == 'nan':
                                item = 'None'
                            try:
                                columns[i].append(literal_eval(item))
                            except Exception:
                                self.__logger.error("Line %i row %s" %
                                                    (i, row))
                                raise
                except Exception:
                    self.__logger.error('Error reading line %i' % length)
                    raise
        except IOError:
            raise
        except Exception:
            raise

        array = []
        for column in columns:
            try:
                array.append(pa.array(column))
            except Exception:
                self.__logger.error("Cannot convert list to pyarrow arrow")
                raise
        try:
            rbatch = pa.RecordBatch.from_arrays(array, schema)
        except Exception:
            self.__logger.error("Cannot convert arrays to batch")
            raise

        return rbatch

    @timethis
    def pyarrow_parsing(self, block):
        # create pyarrow buffer from raw bytes
        buf_ = pa.py_buffer(block)
        try:
            table = read_csv(buf_, ReadOptions())
        except Exception:
            self.__logger.error("Problem converting csv to table")
            raise

        return table

    def execute(self, element):

        raw_ = element.get_data()
        _finfo = self.jobops.meta.data[-1]
        schema = [x.name for x in _finfo.schema.columns]
        self.__logger.debug('Expected header %s' % schema)
        columns = [[] for _ in range(len(schema))]
        length = 0

        try:
            rbatch, time_ = self.py_parsing(schema, columns, length, raw_)
            self.__timers['pyparse'].append(time_)
            self.hbook.fill(self.name, 'time.pyparse', time_)
        except Exception:
            self.__logger.error("Python parsing fails")
            raise

        try:
            table, time_ = self.pyarrow_parsing(raw_)
            self.__timers['pyarrowparse'].append(time_)
            self.hbook.fill(self.name, 'time.pyarrowparse', time_)
        except Exception:
            self.__logger.error("PyArrow parsing fails")
            raise

        self.__logger.debug("Arrow schema: %s time: ", rbatch.schema)
        self.__logger.debug("Arrow schema: %s time: ", table.schema)

    def finalize(self):
        self.__logger.info("Completed CsvParsing")
        summary = self.jobops.meta.summary
        for key in self.__timers:
            _name = '.'
            _name = _name.join([self.name, 'time', key])
            mu = self.hbook.get_histogram(self.name, 'time.'+key).mean()
            std = self.hbook.get_histogram(self.name, 'time.'+key).std()
            self.__logger.info("%s timing: %2.4f" %
                               (key, mean(self.__timers[key])))
            self.__logger.info("%s timing: %2.4f" % (key, mu))

            # Add to the msg
            msgtime = summary.timers.add()
            msgtime.name = _name
            msgtime.time = mu
            msgtime.std = std
