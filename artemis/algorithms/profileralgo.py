#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © Her Majesty the Queen in Right of Canada, as represented
# by the Minister of Statistics Canada, 2019.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Profiles record batch columns with TDigest
"""

from artemis.externals.tdigest.tdigest import TDigest
from artemis.core.algo import AlgoBase


class ProfilerAlgo(AlgoBase):
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        self.__logger.info("%s: __init__ ProfilerAlgo" % self.name)
        self.reader = None
        self.jobops = None
        self.digests = {}
        self.digests_initalized = False
        self.print_percentiles = True

    def initialize(self):
        self.__logger.info("%s: Initialized ProfilerAlgo" % self.name)

    def book(self):
        pass

    def create_tdigests(self, record_batch):
        tool_digests = {}
        try:
            tool_digests = self.get_tool("tdigesttool").execute(record_batch)
            return tool_digests
        except Exception:
            raise
        return

    def execute(self, record_batch):

        raw_ = record_batch.get_data()

        # Code for understanding the record batch
        # that this algorithim has recived
        # We can break up the record batch into a
        # bunch of columns each column can be passed to the profiler algorithim

        self.__logger.debug(
            "Num cols: %s Num rows: %s", raw_.num_columns, raw_.num_rows
        )

        # Create the map column name -> TDigest from the record batch schema
        # We only do this the first time that this algorithim is called,
        # otherwise we continue

        if not self.digests_initalized:
            batch_schema_names = raw_.schema.names
            batch_columns = raw_.columns

            for i in range(len(batch_columns)):
                digest = TDigest()
                self.digests[batch_schema_names[i]] = digest

            self.digests_initalized = True

        # We now calculate the TDigests using the TDigest tool
        # Declare a list of TDigest objects that
        # will be returned by the tdigest tool
        # We pass the record batch directly to the tdigesttool

        try:
            # This too should return a map column name ->
            # TDigest as per the record batch schema

            tool_digests = self.create_tdigests(raw_)

            keys = tool_digests.keys() & self.digests.keys()

            for key in keys:
                self.digests[key] = self.digests[key] + tool_digests[key]

        except Exception:
            self.__logger.error("TDigest creation fails")
            raise

        # Redundant, it is the same object as the input!
        # element.add_data(raw_)

    def finalize(self):
        self.__logger.info("Completed Profiling")
        # print(self.digests)
        for key, value in self.digests.items():
            # print(key, value)
            self.gate.tbook[key] = value
            # if key == 'Normal':
            # print(value.centroids_to_list())
            if len(value.centroids_to_list()) == 0:
                self.__logger.debug(
                    key + " is not a numeric value " "and does not have a TDigest"
                )
            else:
                pass
