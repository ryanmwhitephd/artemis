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
Steering executes business processes as a computation graph
"""
from collections import OrderedDict

from artemis.utils.utils import range_positive
from artemis.decorators import timethis
from artemis.core.algo import AlgoBase
from artemis.core.tree import Node, Element


class Steering(AlgoBase):
    """Steering manages algorithm execution of a business process graph.

    Attributes
    ---------
        _menu : OrderedDict
            Sorted graph of algorithm names
        _algo_instances : Dict
            Configured algorithm objects
        _chunk_cntr : int
            counter for number of

    Parameters
    ----------
        name : str
            Configured name of algorithm

    Other Parameters
    ----------------

    Returns
    -------

    Raises
    ------

    Examples
    ---------

    """

    def __init__(self, name, **kwargs):
        """
        init method
        """
        super().__init__(name, **kwargs)
        self.__logger.info("%s: __init__ Steering" % self.name)
        self._chunk_cntr = 0
        # Execution graph
        self._menu = OrderedDict()
        self._algo_instances = {}

    def initialize(self):
        """
        initialize method calls from_msg
        """
        self.__logger.info("Initialize Steering")
        self.from_msg()

    def from_msg(self):
        """
        Configure steering from a protobuf msg.
        """
        # Loop over algorithms stored in artemis.core.gate.ArtemisGateSvc config
        # Instantiate each algo and adds to _algo_instances.  Retrieves graph from
        # ArtemisGateSvc.  Loops over nodes in graph and creates execution tree in
        # artemis.core.gate.ArtemisGateSvc tree Adds algos to each node for each node
        # sequence.

        self.__logger.info("Loading menu from protobuf")
        # msg = self.gate.meta.config.menu
        msg = self.gate.menu
        self.__logger.info("Initializing Tree and Algos")

        # Initialize algorithms
        # Look up instance to add to execution graph
        self._algo_instances = {}
        for algo in self.gate.config.algos:
            try:
                self._algo_instances[algo.name] = AlgoBase.from_msg(self.__logger, algo)
            except Exception:
                self.__logger.error("Initializing from protobuf %s", algo.name)
                raise
            try:
                self._algo_instances[algo.name].initialize()
            except Exception:
                self.__logger.error("Cannot initialize algo %s" % algo.name)
                raise
        # Traverse ordered set of execution graphs
        # Traverse nodes in each graph
        # Create the execution tree
        # Each node in the tree holds a sequence of algorithms
        # Each node holds the payload to be accessible to the algorithms
        for graph in msg.graphs:
            for node in graph.nodes:
                self.__logger.debug("graph node %s" % (node.name))
                # Create the nodes for the tree
                if node.name == "initial":
                    self.gate.tree.root = Node(node.name, [])
                    self.gate.tree.add_node(self.gate.tree.root)
                else:
                    self.gate.tree.add_node(Node(node.name, node.parents))

                # Initialize the algorithms
                # Create the execution graph
                algos = []
                for algo in node.algos:
                    self.__logger.debug("%s in graph node %s", algo, node.name)
                    # TODO
                    # Initial node has placeholder algo iorequest
                    # iorequest algo is just a string name
                    # no algo message, in json dict stored as an empty dict
                    if node.name == "initial":
                        algos.append("iorequest")
                        continue
                    algos.append(self._algo_instances[algo])
                self._menu[node.name] = tuple(algos)

        self.gate.tree.update_parents()
        self.gate.tree.update_leaves()

        self.__logger.info("Tree nodes are as follows: %s" % str(self.gate.tree.nodes))
        self.__logger.info("%s: Initialized Steering" % self.name)

    def lock(self):
        """
        Overides the base class lock.
        Controls locking of all algorithm properties
        """
        self.__logger.info("Lock Steering properties")
        self.properties.lock = True
        for key in self._menu:
            algos = self._menu[key]
            for algo in algos:
                if isinstance(algo, str):
                    continue
                algo.lock()

    def book(self):
        """
        book method calls book on all algorithms in the menu
        """
        self.__logger.info("Book")

        for key in self._algo_instances:
            algo = self._algo_instances[key]
            self.__logger.info("Book %s", algo.name)
            bins = [x for x in range_positive(0.0, 100.0, 2.0)]
            try:
                self.gate.hbook.book(
                    self.name, "time." + algo.name, bins, "ms", timer=True
                )
            except Exception:
                self.__logger.error("Cannot book steering")
                raise
            try:
                algo.book()
            except Exception:
                self.__logger.error("Cannot book %s" % algo.name)
        self.__logger.info("HBook keys %s", self.gate.hbook.keys())

    def rebook(self):
        """
        retrieve the sampling times and rebook
        """

        for key in self._menu:
            for algo in self._menu[key]:
                if isinstance(algo, str):
                    self.__logger.debug("Not an algo: %s" % algo)
                else:
                    try:
                        algo.rebook()
                    except Exception:
                        self.__logger.error("Cannot book %s" % algo.name)

    def _element_name(self, key):
        """
        retrieve datastore element name with key.
        """
        # element name may not be unique in case of shared stored
        return (
            self.gate.tree.name
            + "_"
            + self.gate.tree.nodes[key].key
            + "_"
            + str(self._chunk_cntr)
        )

    def execute(self, payload):
        """
        Prepares payload for algorithms and controls the algorithm execution.

        Parameters
        ----------
        payload : pyarrow.buffer
            Expected that payload is a pyarrow buffer.

        Raises
        ------
            Exception
        """
        self.__logger.debug("Execute %s" % self.name)

        # Traverse the menu graph
        # Retrieve list of algo names for each sequence in a node
        # Use the tree to create an Element to hold the payload
        # Initial node must obtain the payload from Artemis
        # Subsequent nodes retrieve the input payload from the output of parent node
        for key in self._menu:
            algos = self._menu[key]
            self.__logger.debug("Menu input element: %s" % key)
            # TODO -- Continue work regarding gettting parent data, etc.
            self.gate.tree.nodes[key].payload.append(Element(self._element_name(key)))
            self.__logger.debug("Element: %s" % self._element_name)
            if key == "initial":
                self.gate.tree.nodes[key].payload[-1].add_data(payload)
            else:
                for parent in self.gate.tree.nodes[key].parents:
                    # When retrieving input data, we are duplicating data
                    # adding the input data as part of the new element
                    # with that element key
                    self.gate.tree.nodes[key].payload[-1].add_data(
                        self.gate.tree.nodes[parent].payload[-1].get_data()
                    )

            for algo in algos:
                # TODO -- ensure the algos are actually type <class AlgoBase>
                if isinstance(algo, str):
                    self.__logger.debug("Not an algo: %s" % algo)
                else:
                    self.__logger.debug("Type: %s" % type(algo))
                    # Timing decorator / wrapper
                    _algexe = timethis(algo.execute)
                    try:
                        time_ = _algexe(self.gate.tree.nodes[key].payload[-1])[-1]
                        self.gate.hbook.fill(self.name, "time." + algo.name, time_)
                    except Exception:
                        raise

        self._chunk_cntr += 1

    def finalize(self):
        """
        finalize method calls finalize on all algorithms in menu
        """
        self.__logger.info("Completed steering")
        for key in self._menu:
            for algo in self._menu[key]:
                if isinstance(algo, str):
                    self.__logger.debug("Not an algo: %s" % algo)
                else:
                    algo.finalize()
