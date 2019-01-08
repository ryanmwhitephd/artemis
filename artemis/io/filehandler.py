#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2019 Ryan Mackenzie White <ryan.white4@canada.ca>
#
# Distributed under terms of the  license.

"""
Generic tool for reading raw bytes into Arrow buffer
Aimed for handling ascii encoded files, e.g.
tab delimited or legacy data
Support for:
Chunking data in bytes
Scanning for line delimiter
Extracting meta data from a header
"""
import io

from artemis.core.tool import ToolBase


class FileHandlerTool(ToolBase):

    def __init__(self, name, **kwargs):
        defaults = self._set_defaults()
        # Override the defaults from the kwargs
        for key in kwargs:
            defaults[key] = kwargs[key]
        super().__init__(name, **defaults)
        self._delimiter = None
        self._offset_header = None
        self.__logger.info('%s: __init__ FileHandlerTool' % self.name)

    def _set_defaults(self):
        defaults = {'blocksize': 2**27,
                    'separator': ',',
                    'delimiter': '\r\n',
                    'skip_header': False,
                    'offset_header': 0}

        return defaults

    def encode_delimiter(self):
        self._delimiter = bytes(self.properties.delimiter, 'utf8')

    def initialize(self):
        self.__logger.info("%s properties: %s",
                           self.__class__.__name__,
                           self.properties)
        self.encode_delimiter()
        self._offset_header = self.properties.offset_header

    def prepare(self, file_):
        '''
        try to read the first line of file
        filehandle, f, is pa.PythonFile
        '''
        if file_.tell() != 0:
            file_.seek(0)

        header = file_.readline()
        offset = file_.tell()  # Do we start of offset, or offset + byte
        meta = header.decode().rstrip(self.properties.delimiter).\
            split(self.properties.separator)

        file_.seek(0)
        self._offset_header = offset
        return header, meta, offset

    def _create_header(self, schema):
        linesep = self.properties.delimiter
        csv = io.StringIO()
        csv.write(u",".join(schema))
        csv.write(linesep)

        # bytes object with unicode encoding
        csv = csv.getvalue().encode()
        return bytearray(csv)

    def _seek_delimiter(self, file_, delimiter, blocksize):
        '''
        Dask-like line delimiter
        to read by bytes and seek to nearest line
        default block_size 2**16 or 64 bytes

        BUG
        Last block is not at EOF???
        '''
        if file_.tell() == 0:
            return

        last = b''
        while True:
            current = file_.read(blocksize)
            if not current:
                return
            full = last + current
            try:
                i = full.index(delimiter)
                file_.seek(file_.tell() - (len(full) - i) + len(delimiter))
                return
            except (OSError, ValueError):
                print("Problem at last seek")
            last = full[-len(delimiter):]

    def _get_block(self, file_, offset, length, size, delimiter=None):
        '''
        Dask-like block read of data in bytes
        Returns the length of bytes to read for a block
        starts at last position in file, does not ensure that
        file is already at position after delimiter

        Requries starting offset to be after delimiter

        # TODO, if offset not a delimiter seek to the next one

        # BUG last seek goes past EOF
        '''
        if offset != file_.tell():  # commonly both zero
            file_.seek(offset)

        if not offset and length is None and file_.tell() == 0:
            return file_.read()

        if delimiter:
            # TODO
            # If initial block and not at file start
            # Find the first delimiter?
            start = file_.tell()
            length -= start - offset
            if (start+length) > size:
                length = size - start
            # BUG - No Exception thrown on seek past last byte in object
            try:
                file_.seek(start + length)
                self._seek_delimiter(file_, delimiter, 2**16)
            except (OSError, ValueError):
                file_.seek(0, 2)
            end = file_.tell()

            offset = start
            length = end - start

        return offset, length

    def _read_block(self, file_, offset, length, delimiter=None):
        '''
        Dask-like block read of data in bytes
        Ensures the start point of a block is after a delimiter
        '''
        if offset != file_.tell():  # commonly both zero
            file_.seek(offset)

        if not offset and length is None and file_.tell() == 0:
            return file_.read()

        if delimiter:
            self._seek_delimiter(file_, delimiter, 2**16)
            start = file_.tell()
            length -= start - offset

            try:
                file_.seek(start + length)
                self._seek_delimiter(file_, delimiter, 2**16)
            except (OSError, ValueError):
                file_.seek(0, 2)

            end = file_.tell()

            offset = start
            length = end - start

            file_.seek(offset)
        return file_.read(length)

    def readinto_block(self, file_, bobj, offset, schema=None):
        '''
        Dask-like block read of data in bytes
        Assumes length of block fixed and preallocated bytearray provided
        Assumes the blocksize and line delimiter already handled

        # Requires inserting header into each block
        '''
        if schema is None:
            if offset != file_.tell():
                file_.seek(offset)
            return file_.readinto(bobj)
        else:
            block_ = self._create_header(schema)

            if offset != file_.tell():
                file_.seek(offset)
            file_.readinto(bobj)
            block_.extend(bobj)
            return block_

    def execute(self, file_):
        '''
        Creates a generator to return blocks of data from IO bytestream

        Parameters
        ---------
        file_ : pyarrow NativeFile

        '''
        # Seek to end (0 bytes relative to the end)
        file_.seek(0, 2)
        fsize = file_.tell()
        if self.properties.skip_header:
            file_.seek(self._offset_header)
        else:
            file_.seek(0)
        pos = file_.tell()
        blocks = []  # tuples of length two (offset, length)
        while file_.tell() < fsize:
            if pos == 0 and self._offset_header is not None:
                size = self.properties.blocksize + \
                    self._offset_header
            else:
                size = self.properties.blocksize
            blocks.append(self._get_block(file_,
                                          pos,
                                          size,
                                          fsize,
                                          self._delimiter))
            pos = file_.tell()

        # Seek back to start
        file_.seek(0)
        return blocks