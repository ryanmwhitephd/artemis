#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2018 Ryan Mackenzie White <ryan.white4@canada.ca>
#
# Distributed under terms of the  license.

"""

"""
import unittest
import logging
import json

from artemis.core.dag import Sequence, Chain, Menu
from artemis.algorithms.dummyalgo import DummyAlgo1
from artemis.algorithms.csvparseralgo import CsvParserAlgo
from artemis.artemis import Artemis
from artemis.core.singleton import Singleton
from artemis.core.properties import JobProperties
from artemis.generators.generators import GenCsvLikeArrow

logging.getLogger().setLevel(logging.INFO)


class ArtemisTestCase(unittest.TestCase):

    def setUp(self):
        self.menucfg = 'arrow_testmenu.json'
        self.gencfg = 'arrow_testgen.json'

        print("================================================")
        print("Beginning new TestCase %s" % self._testMethodName)
        print("================================================")
        testalgo = DummyAlgo1('dummy', myproperty='ptest', loglevel='INFO')
        csvalgo = CsvParserAlgo('csvparser')

        seq1 = Sequence(["initial"], (testalgo, testalgo), "seq1")
        seq2 = Sequence(["initial"], (testalgo, testalgo), "seq2")
        seq3 = Sequence(["seq1", "seq2"], (testalgo,), "seq3")
        seq4 = Sequence(["seq3"], (testalgo,), "seq4")

        dummyChain1 = Chain("dummy1")
        dummyChain1.add(seq1)
        dummyChain1.add(seq4)
        dummyChain1.add(seq3)
        dummyChain1.add(seq2)

        seq5 = Sequence(["initial"], (testalgo, testalgo), "seq5")
        seq6 = Sequence(["seq5"], (testalgo, testalgo), "seq6")
        seq7 = Sequence(["seq6"], (testalgo,), "seq7")

        dummyChain2 = Chain("dummy2")
        dummyChain2.add(seq5)
        dummyChain2.add(seq6)
        dummyChain2.add(seq7)

        csvChain = Chain("csvchain")
        seqX = Sequence(["initial"], (csvalgo,), "seqX")
        csvChain.add(seqX)

        testmenu = Menu("test")
        testmenu.add(dummyChain1)
        testmenu.add(dummyChain2)
        testmenu.add(csvChain)
        testmenu.generate()
        try:
            testmenu.to_json(self.menucfg)
        except Exception:
            raise

        generator = GenCsvLikeArrow('generator',
                                    nbatches=1,
                                    num_cols=20,
                                    num_rows=10000)
        try:
            with open(self.gencfg, 'x') as ofile:
                json.dump(generator.to_dict(), 
                          ofile, 
                          indent=4)
        except Exception:
            raise

    def tearDown(self):
        Singleton.reset(JobProperties)

    def test_control(self):
        print("Testing the Artemis Prototype")
        bow = Artemis("arrow", 
                      menu=self.menucfg, 
                      generator=self.gencfg,
                      blocksize=2**16,
                      skip_header=True,
                      loglevel='INFO')
        bow.control()


if __name__ == '__main__':
    unittest.main()
