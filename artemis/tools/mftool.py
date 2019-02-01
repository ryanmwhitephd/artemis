#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2019 Dominic Parent <dominic.parent@canada.ca>
#
# Distributed under terms of the  license.

"""
Tool that reads mainframe files encoded in the EBCDIC format.
"""

import pyarrow as pa
from artemis.core.tool import ToolBase


class MfTool(ToolBase):
    '''
    The class that deals with mainframe files.
    '''
    def __init__(self, ds_schema):
        '''
        Initiate a reader with parameters. The reader can be reused.
        '''
        self.ds_schema = ds_schema
        self.nrecords = len(ds_schema)
        self.pos_char = {'{': '0', 'a': '1', 'b': '2', 'c': '3', 'd': '4',
                         'e': '5', 'f': '6', 'g': '7', 'h': '8', 'i': '9'}
        self.neg_char = {'j': '0', 'k': '1', 'l': '2', 'm': '3', 'n': '4',
                         'o': '5', 'p': '6', 'q': '7', 'r': '8', 's': '9'}
        self.rsize = 0
        for ds in self.ds_schema:
            self.rsize = self.rsize + ds['length']

    def execute(self, block):
        '''
        Reads a block of data with the initialized MfTool object.
        '''

        # The block is decoded from the cp500 code page.
        block = block.decode('cp500')

        isize = len(block)
        print(isize)
        odata = []
        arrowodata = []
        nrecords = len(self.ds_schema)

        # Create a list of empty lists for the number of columns.
        for field in self.ds_schema:
            odata.append([])

        ccounter = 0
        ncounter = 0
        fcounter = 0

        while ccounter < isize:
            # Extract record.
            rdata = block[ccounter: (ccounter + self.rsize)]
            while ncounter < nrecords:
                # Extract field.
                field = rdata[fcounter:
                             (fcounter + self.ds_schema[ncounter]['length'])]
                # Processes each field according to the datatype.
                if self.ds_schema[ncounter]['utype'] == 'int':
                    # Replacing the end character with a proper digit requires
                    # differentiating between negative and positive numbers.
                    if field[-1:] in self.pos_char:
                        # Padding zeroes are taken removed by type conversion.
                        field = int(field.replace(field[-1:],
                                                  self.pos_char[field[-1:]]))
                    else:
                        field = field.replace(field[-1:],
                                              self.neg_char[field[-1:]])
                        field = int('-' + field)
                    odata[ncounter].append(field)
                elif self.ds_schema[ncounter]['utype'] == 'str':
                    # Removes padding spaces from the data.
                    odata[ncounter].append(field.strip())
                elif self.ds_schema[ncounter]['utype'] == 'uint':
                    odata[ncounter].append(int(field))
                fcounter = fcounter + self.ds_schema[ncounter]['length']
                ncounter = ncounter + 1
            ncounter = 0
            fcounter = 0
            ccounter = ccounter + self.rsize

        # Creates apache arrow dataset.
        for my_list in odata:
            arrowodata.append(pa.array(my_list))

        print('Output data lists.')
        print(odata)

        print('Output data arrow arrays.')
        print(arrowodata)

        return arrowodata