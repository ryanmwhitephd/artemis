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

"""
from artemis.logger import Logger
from artemis.decorators import iterable

from artemis.configurables.configurable import Configurable
from artemis.configurables.configurable import GlobalConfigOptions
from artemis.tools.csvtool import CsvTool


@iterable
class CsvGenOptions:
    generator_type = "csv"
    filehandler_type = "csv"
    nbatches = 10
    num_cols = 20
    num_rows = 10000
    linesep = "\r\n"
    delimiter = ","
    blocksize = 2 ** 16


@Logger.logged
class CsvGenConfig(Configurable):
    def __init__(self, menu=None, **kwargs):
        options = dict(GlobalConfigOptions())
        options.update(dict(CsvGenOptions()))
        options.update(kwargs)
        super().__init__(menu, **options)
        self.__logger.info(options)

    def configure(self):

        self._config_generator(
            nbatches=self.nbatches,
            # num_cols=self.num_cols,
            table_id=self.table_id,
            num_rows=self.num_rows,
            seed=self.seed,
        )

        self._config_filehandler(
            blocksize=self.blocksize, delimiter=self.delimiter, seed=self.seed
        )

        self._config_tdigest()

        # Ensure block_size for arrow parser greater than
        # file chunk size
        csvtool = CsvTool("csvtool", block_size=(2 * self.blocksize))
        self._tools.append(csvtool.to_msg())
        self._config_sampler()
        self._config_writer()
        self._add_tools()
        self.__logger.info(self._msg)


@Logger.logged
class CsvIOConfig(Configurable):
    def __init__(self, menu=None, **kwargs):
        options = dict(GlobalConfigOptions())
        options.update(dict(CsvGenOptions()))
        options.update(kwargs)
        super().__init__(menu, **options)

    def configure(self):
        self._config_generator(
            path=self.input_repo,
            glob=self.input_glob,
            nbatches=self.nbatches,
            seed=self.seed,
        )

        self._config_filehandler(
            blocksize=self.blocksize, delimiter=self.delimiter, seed=self.seed
        )

        self._config_tdigest()

        # Ensure block_size for arrow parser greater than
        # file chunk size
        csvtool = CsvTool("csvtool", block_size=(self.blocksize * 2))
        self._tools.append(csvtool.to_msg())
        self._config_sampler()
        self._config_writer()
        self._add_tools()
        self.__logger.info(self._msg)
