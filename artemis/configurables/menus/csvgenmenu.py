#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2019 Ryan Mackenzie White <ryan.white4@canada.ca>
#
# Distributed under terms of the  license.

"""

"""
from artemis.configurables.configurable import MenuBuilder
from artemis.algorithms.dummyalgo import DummyAlgo1
from artemis.algorithms.csvparseralgo import CsvParserAlgo
from artemis.algorithms.profileralgo import ProfilerAlgo
from artemis.meta.Directed_Graph import Directed_Graph, Node


class CsvGenMenu(MenuBuilder):

    def __init__(self, name='test'):
        super().__init__(name)

    def _algo_builder(self):
        '''
        define all algorithms required
        '''
        self._algos['testalgo'] = DummyAlgo1('dummy',
                                             myproperty='ptest',
                                             loglevel='INFO')
        self._algos['csvalgo'] = CsvParserAlgo('csvparser', loglevel='INFO')
        self._algos['profileralgo'] = ProfilerAlgo('profiler', loglevel='INFO')

    def _seq_builder(self):
        self._seqs['seq1'] = Node(["initial"],
                                  ('dummy', 'dummy'),
                                  "seq1")
        self._seqs['seq2'] = Node(["initial"],
                                  ('dummy', 'dummy'),
                                  "seq2")
        self._seqs['seq3'] = Node(["seq1", "seq2"],
                                  ('dummy',),
                                  "seq3")
        self._seqs['seq4'] = Node(["seq3"],
                                  ('dummy',),
                                  "seq4")

        self._seqs['seq5'] = Node(["initial"],
                                  ('dummy', 'dummy'),
                                  "seq5")
        self._seqs['seq6'] = Node(["seq5"],
                                  ('dummy', 'dummy'),
                                  "seq6")
        self._seqs['seq7'] = Node(["seq6"],
                                  ('dummy',),
                                  "seq7")

        self._seqs['seqX'] = Node(["initial"],
                                  ('csvparser',),
                                  "seqX")
        self._seqs['seqY'] = Node(["seqX"],
                                  ('profiler',),
                                  "seqY")

    def _chain_builder(self):
        self._chains['dummyChain1'] = Directed_Graph("dummy1")
        self._chains['dummyChain1'].add(self._seqs['seq1'])
        self._chains['dummyChain1'].add(self._seqs['seq4'])
        self._chains['dummyChain1'].add(self._seqs['seq3'])
        self._chains['dummyChain1'].add(self._seqs['seq2'])

        self._chains['dummyChain2'] = Directed_Graph("dummy2")
        self._chains['dummyChain2'].add(self._seqs['seq5'])
        self._chains['dummyChain2'].add(self._seqs['seq6'])
        self._chains['dummyChain2'].add(self._seqs['seq7'])

        self._chains['csvchain'] = Directed_Graph("csvchain")
        self._chains['csvchain'].add(self._seqs['seqX'])
        self._chains['csvchain'].add(self._seqs['seqY'])
