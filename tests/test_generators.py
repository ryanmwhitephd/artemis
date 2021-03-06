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
import unittest
import logging
import csv
import io
import tempfile
import os
import uuid
import itertools

from ast import literal_eval
import pyarrow as pa
from pyarrow.csv import read_csv, ReadOptions

from artemis.generators.csvgen import GenCsvLike, GenCsvLikeArrow 
from artemis.generators.filegen import FileGenerator
from artemis.generators.common import BuiltinsGenerator

from artemis.meta.cronus import BaseObjectStore
from artemis.io.protobuf.cronus_pb2 import TableObjectInfo
from artemis.io.protobuf.table_pb2 import Table
logging.getLogger().setLevel(logging.INFO)


class GeneratorTestCase(unittest.TestCase):

    def setUp(self):
        print("================================================")
        print("Beginning new TestCase %s" % self._testMethodName)
        print("================================================")

    def tearDown(self):
        pass
    
    def setupStore(selfi, dirpath):
        store = BaseObjectStore(dirpath, 'artemis')
        g_dataset = store.register_dataset()
        store.new_partition(g_dataset.uuid, 'generator')
        job_id = store.new_job(g_dataset.uuid)
        
        # define the schema for the data
        g_table = Table()
        g_table.name = 'generator'
        g_table.uuid = str(uuid.uuid4())
        g_table.info.schema.name = 'csv'
        g_table.info.schema.uuid = str(uuid.uuid4())

        fields = list(itertools.islice(GenCsvLikeArrow.generate_col_names(),20))
        for f in fields:
            field = g_table.info.schema.info.fields.add()
            field.name = f
        
        tinfo = TableObjectInfo()
        tinfo.fields.extend(fields)
        id_ = store.register_content(g_table, 
                               tinfo, 
                               dataset_id=g_dataset.uuid,
                               job_id=job_id,
                               partition_key='generator').uuid
        return store, g_dataset.uuid, job_id, id_

    def test_xgen(self):
        generator = GenCsvLike()
        generator.nchunks = 1
        ichunk = 0
        for chunk in generator.generate():
            print('Test chunk %s' % ichunk)
            ichunk += 1
    
    def chunker(self):
        nbatches = 1
        generator = GenCsvLikeArrow('test')
        for ibatch in range(nbatches):
            yield generator.make_random_csv()

    def test_genarrow(self):
        with tempfile.TemporaryDirectory() as dirpath:
            store, ds_id, job_id, tbl_id = self.setupStore(dirpath)
            
            generator = GenCsvLikeArrow('test',
                                        nbatches=1,
                                        table_id=tbl_id)
            generator.gate.meta.parentset_id = ds_id
            generator.gate.meta.job_id = str(job_id)
            generator.gate.store = store
            generator.initialize()
            for batch in range(1):
                print(generator.make_random_csv())

    #def test_chunker(self):
    #    for batch in self.chunker():
    #        print(batch)

    def test_batch(self):
        with tempfile.TemporaryDirectory() as dirpath:
            store, ds_id, job_id, tbl_id = self.setupStore(dirpath)
            
            generator = GenCsvLikeArrow('test',table_id=tbl_id)
            generator.gate.meta.parentset_id = ds_id
            generator.gate.meta.job_id = str(job_id)
            generator.gate.store = store
            generator.initialize()
            
            data, names, batch = generator.make_random_csv()

    def test_read_StringIO(self):
        with tempfile.TemporaryDirectory() as dirpath:
            store, ds_id, job_id, tbl_id = self.setupStore(dirpath)
            
            generator = GenCsvLikeArrow('generator',
                                        nbatches=1,
                                        table_id=tbl_id)
            generator.gate.meta.parentset_id = ds_id
            generator.gate.meta.job_id = str(job_id)
            generator.gate.store = store
            generator.initialize()
            # data is byte encoded
            data, names, batch = generator.make_random_csv()
            # Get the StringIO object
            # To be ready to pass to reader
            bytesio = io.BytesIO(data).read().decode()
            stringio = io.StringIO(bytesio)

            for row in csv.reader(stringio):
                print(row)
    
    def test_read_TextIO(self):
        with tempfile.TemporaryDirectory() as dirpath:
            store, ds_id, job_id, tbl_id = self.setupStore(dirpath)
            
            generator = GenCsvLikeArrow('generator',
                                        nbatches=1,
                                        table_id=tbl_id)
            generator.gate.meta.parentset_id = ds_id
            generator.gate.meta.job_id = str(job_id)
            generator.gate.store = store
            generator.initialize()
            # csvlike is byte encoded
            data, names, batch = generator.make_random_csv()
            # Get the Text IO object
            # To be ready to pass to reader
            textio = io.TextIOWrapper(io.BytesIO(data))

            for row in csv.reader(textio):
                print(row)

    def test_arrowbuf(self):

        with tempfile.TemporaryDirectory() as dirpath:
            store, ds_id, job_id, tbl_id = self.setupStore(dirpath)
            
            generator = GenCsvLikeArrow('test',
                                        nbatches=1,
                                        table_id=tbl_id)
            generator.gate.meta.parentset_id = ds_id
            generator.gate.meta.job_id = str(job_id)
            generator.gate.store = store
            generator.initialize()
            
            data, names, batch = generator.make_random_csv()
            
            # Create the pyarrow buffer, zero-copy view 
            # to the csvbytes objet
            buf = pa.py_buffer(data)
            print('Raw bytes from generator')
            print(data)
            print('PyArrow Buf')
            print(buf)
            print(buf.to_pybytes())
            table = read_csv(buf)
            print(table.schema)

    def test_read_csv(self):
        
        with tempfile.TemporaryDirectory() as dirpath:
            store, ds_id, job_id, tbl_id = self.setupStore(dirpath)
            
            generator = GenCsvLikeArrow('generator',
                                        nbatches=1,
                                        table_id=tbl_id)
            generator.gate.meta.parentset_id = ds_id
            generator.gate.meta.job_id = str(job_id)
            generator.gate.store = store
            generator.initialize()
        
            data, names, batch = generator.make_random_csv()
            # textio = io.TextIOWrapper(io.BytesIO(data))
            columns = [[] for _ in range(generator.num_cols)]
            
            with io.TextIOWrapper(io.BytesIO(data)) as textio:
                header = next(csv.reader(textio))

                assert(header == names)
                assert(names == batch.schema.names)
                
                for row in csv.reader(textio):
                    for i, item in enumerate(row):
                        if item == 'nan':
                            item = 'None'
                        columns[i].append(literal_eval(item))
            
            array = []
            for column in columns:
                array.append(pa.array(column))
            rbatch = pa.RecordBatch.from_arrays(array, header)
            assert(batch.schema.names == names)
            assert(batch.schema == rbatch.schema)
    
    def test_read_mixed_csv(self):
        with tempfile.TemporaryDirectory() as dirpath:
            store, ds_id, job_id, tbl_id = self.setupStore(dirpath)
            
            generator = GenCsvLikeArrow('generator',
                                        nbatches=1,
                                        table_id=tbl_id)
            generator.gate.meta.parentset_id = ds_id
            generator.gate.meta.job_id = str(job_id)
            generator.gate.store = store
            generator.initialize()
            data, names, batch = generator.make_mixed_random_csv()
            textio = io.TextIOWrapper(io.BytesIO(data))
            columns = [[] for _ in range(generator.num_cols)]
            header = next(csv.reader(textio))
            
            assert(header == names)
            assert(names == batch.schema.names)
            
            for row in csv.reader(textio):
                for i, item in enumerate(row):
                    if item == 'nan':
                        item = 'None'
                    columns[i].append(literal_eval(item))
           
            array = []
            for column in columns:
                array.append(pa.array(column))
            rbatch = pa.RecordBatch.from_arrays(array, header)
            # Relies on the literal type conversion to python types first
            # Arrow then converts a python array of type<x> to pa array of type<x>
            assert(batch.schema.names == names)
            assert(batch.schema == rbatch.schema)
    
    def test_write_mixed_csv(self):
        with tempfile.TemporaryDirectory() as dirpath:
            store, ds_id, job_id, tbl_id = self.setupStore(dirpath)
            
            generator = GenCsvLikeArrow('generator',
                                        nbatches=4,
                                        table_id=tbl_id, num_rwows=10000)
            generator.gate.meta.parentset_id = ds_id
            generator.gate.meta.job_id = str(job_id)
            generator.gate.store = store
            generator.initialize()


            data, col_names, batch = generator.make_mixed_random_csv()
            with tempfile.TemporaryDirectory() as dirpath:
                _fname = os.path.join(dirpath, 'test.dat')
                with pa.OSFile(_fname, 'wb') as sink:
                    writer = pa.RecordBatchFileWriter(sink, batch.schema)
                    i = 0
                    for _ in range(10):
                        print("Generating batch ", i)
                        data, batch = next(generator.generate())
                        writer.write_batch(batch)
                        i += 1
                    writer.close()
   
    def test_continuous_write(self):
        
        with tempfile.TemporaryDirectory() as dirpath:
            store = BaseObjectStore(dirpath, 'artemis')
            g_dataset = store.register_dataset()
            store.new_partition(g_dataset.uuid, 'test')
            job_id = store.new_job(g_dataset.uuid)
            
            # define the schema for the data
            g_table = Table()
            g_table.name = 'generator'
            g_table.uuid = str(uuid.uuid4())
            g_table.info.schema.name = 'csv'
            g_table.info.schema.uuid = str(uuid.uuid4())

            fields = list(itertools.islice(GenCsvLikeArrow.generate_col_names(),20))
            for f in fields:
                field = g_table.info.schema.info.fields.add()
                field.name = f
            
            tinfo = TableObjectInfo()
            tinfo.fields.extend(fields)
            id_ = store.register_content(g_table, 
                                   tinfo, 
                                   dataset_id=g_dataset.uuid,
                                   job_id=job_id,
                                   partition_key='test').uuid

            
            generator = GenCsvLikeArrow('test', 
                                        nbatches=4,
                                        num_rows=10000,
                                        table_id=id_)
            generator.gate.meta.parentset_id = g_dataset.uuid
            generator.gate.meta.job_id = str(job_id)
            generator.gate.store = store
            generator.initialize()

            data, col_names, batch = generator.make_mixed_random_csv()
            
            schema = batch.schema
            sink = pa.BufferOutputStream()
            writer = pa.RecordBatchFileWriter(sink, schema)
            i = 0
            ifile = 0
            batch = None
            print("Size allocated ", pa.total_allocated_bytes())
            for data, batch in generator.generate(): 
                print("Generating batch ", i)
                print("Size allocated ", pa.total_allocated_bytes())
                if pa.total_allocated_bytes() < int(20000000):
                    print("Writing to buffer ", batch.num_rows)
                    writer.write_batch(batch)
                else:
                    print("Flush to disk ", pa.total_allocated_bytes())
                    _fname = os.path.join(dirpath,'test_'+str(ifile)+'.dat')
                    
                    buf = sink.getvalue()
                    with pa.OSFile(_fname, 'wb') as f:
                        try:
                            f.write(buf)
                        except Exception:
                            print("Bad idea")
                    print("Size allocated ", pa.total_allocated_bytes())
                    ifile += 1
                    # Batch still needs to be written
                    sink = pa.BufferOutputStream()
                    writer = pa.RecordBatchFileWriter(sink, schema)
                    writer.write_batch(batch)
                i += 1
            
            batch = None

            print("Size allocated ", pa.total_allocated_bytes())

    def test_write_buffer_csv(self):
        with tempfile.TemporaryDirectory() as dirpath:
            store, ds_id, job_id, tbl_id = self.setupStore(dirpath)
            
            generator = GenCsvLikeArrow('generator',
                                        nbatches=4,
                                        table_id=tbl_id, num_rwows=10000)
            generator.gate.meta.parentset_id = ds_id
            generator.gate.meta.job_id = str(job_id)
            generator.gate.store = store
            generator.initialize()

            data, col_names, batch = generator.make_mixed_random_csv()
            sink = pa.BufferOutputStream()
            writer = pa.RecordBatchFileWriter(sink, batch.schema)
            i = 0
            _sum_size = 0 
            for _ in range(2):
                print("Generating batch ", i)
                data, batch = next(generator.generate())
                writer.write_batch(batch)
                _sum_size += pa.get_record_batch_size(batch)
                i += 1
            batch = None
            print("Size allocated ", pa.total_allocated_bytes())
            print("Sum size serialized ", _sum_size) 
            if pa.total_allocated_bytes() < 20000000:
                for _ in range(2):
                    print("Generating batch ", i)
                    data, batch = next(generator.generate())
                    writer.write_batch(batch)
                    _sum_size += pa.get_record_batch_size(batch)
                    i += 1
                batch = None
                print("Size allocated ", pa.total_allocated_bytes())
                print("Sum size serialized ", _sum_size) 
            writer.close() 
            try:
                sink.flush()
            except ValueError:
                print("Cannot flush")

            buf = sink.getvalue() 
            print("Size in buffer ", buf.size)
            print("Size allocated ", pa.total_allocated_bytes())

            reader = pa.RecordBatchFileReader(pa.BufferReader(buf))
            print(reader.num_record_batches)
            with tempfile.TemporaryDirectory() as dirpath:
                _fname = os.path.join(dirpath, 'test.dat')
                with pa.OSFile(_fname, 'wb') as f:
                    try:
                        f.write(buf)
                    except Exception:
                        print("Bad idea")
            
                file_obj = pa.OSFile(_fname)
                reader = pa.open_file(file_obj)
                print(reader.num_record_batches)
     
    def test_pyarrow_read_mixed_csv(self):
        with tempfile.TemporaryDirectory() as dirpath:
            store, ds_id, job_id, tbl_id = self.setupStore(dirpath)
            
            generator = GenCsvLikeArrow('test',
                                        nbatches=1,
                                        table_id=tbl_id)
            generator.gate.meta.parentset_id = ds_id
            generator.gate.meta.job_id = str(job_id)
            generator.gate.store = store
            generator.initialize()
            data, names, batch = generator.make_mixed_random_csv()
            assert(names == batch.schema.names)
            buf = pa.py_buffer(data)
            table = read_csv(buf, ReadOptions())
            assert(len(data) == buf.size)
            try:
                assert(batch.schema == table.schema)
            except AssertionError:
                print("Expected schema")
                print(batch.schema)
                print("Inferred schema")
                print(table.schema)

    def test_pyarrow_read_csv(self):
        with tempfile.TemporaryDirectory() as dirpath:
            store, ds_id, job_id, tbl_id = self.setupStore(dirpath)
            
            generator = GenCsvLikeArrow('test',
                                        nbatches=1,
                                        table_id=tbl_id)
            generator.gate.meta.parentset_id = ds_id
            generator.gate.meta.job_id = str(job_id)
            generator.gate.store = store
            generator.initialize()
            
            data, names, batch = generator.make_random_csv()
            assert(names == batch.schema.names)
            buf = pa.py_buffer(data)
            table = read_csv(buf, ReadOptions())
            assert(len(data) == buf.size)
            try:
                assert(batch.schema == table.schema)
            except AssertionError:
                print("Expected schema")
                print(batch.schema)
                print("Inferred schema")
                print(table.schema)
            return table
    
    def test_writecsv(self):
        with tempfile.TemporaryDirectory() as dirpath:
            store, ds_id, job_id, tbl_id = self.setupStore(dirpath)
            
            generator = GenCsvLikeArrow('generator',
                                        nbatches=4,
                                        table_id=tbl_id, num_rwows=10000)
            generator.gate.meta.parentset_id = ds_id
            generator.gate.meta.job_id = str(job_id)
            generator.gate.store = store
            generator.initialize()
            generator.write()

    def test_filegenerator(self):
        with tempfile.TemporaryDirectory() as dirpath:
            store = BaseObjectStore(dirpath, 'artemis')
            g_dataset = store.register_dataset()
            store.new_partition(g_dataset.uuid, 'test')
            job_id = store.new_job(g_dataset.uuid)
            
            # define the schema for the data
            g_table = Table()
            g_table.name = 'generator'
            g_table.uuid = str(uuid.uuid4())
            g_table.info.schema.name = 'csv'
            g_table.info.schema.uuid = str(uuid.uuid4())

            fields = list(itertools.islice(GenCsvLikeArrow.generate_col_names(),20))
            for f in fields:
                field = g_table.info.schema.info.fields.add()
                field.name = f
            
            tinfo = TableObjectInfo()
            tinfo.fields.extend(fields)
            id_ = store.register_content(g_table, 
                                   tinfo, 
                                   dataset_id=g_dataset.uuid,
                                   job_id=job_id,
                                   partition_key='test').uuid

            generator = GenCsvLikeArrow('test', 
                    nbatches=3, 
                    file_type = 1,
                    table_id=id_)
            
            generator.gate.meta.parentset_id = g_dataset.uuid
            generator.gate.meta.job_id = str(job_id)
            generator.gate.store = store
            generator.initialize()
            generator.write()
            generator = FileGenerator('test', path=dirpath, glob='.csv')
            generator.gate.meta.parentset_id = g_dataset.uuid
            generator.gate.meta.job_id = str(job_id)
            generator.gate.store = store
            generator.initialize()
            batches = 0
            for item in generator:
                print(item)
                batches += 1
            assert(batches == 3)
            generator.reset()
            for item in generator.sampler():
                print(item)
            #iter_ = generator.generate()
            #print(next(iter_))

    def test_multiple(self):
        print("Testing multiple generators with same seed")
        gen1 = BuiltinsGenerator(42)
        gen2 = BuiltinsGenerator(42)

        print(gen1.generate_int_list(10, 0.1))
        print(gen2.generate_int_list(10, 0.1))

    def test_iter_csv(self):
        with tempfile.TemporaryDirectory() as dirpath:
            store, ds_id, job_id, tbl_id = self.setupStore(dirpath)
            
            generator = GenCsvLikeArrow('generator',
                                        nbatches=4,
                                        table_id=tbl_id,
                                        num_rows=10000)
            generator.gate.meta.parentset_id = ds_id
            generator.gate.meta.job_id = str(job_id)
            generator.gate.store = store
            generator.initialize()

            nbatch = 0
            for batch in generator:
                nbatch += 1

            assert(nbatch == 4)

            nsamples = 0
            for batch in generator.sampler():
                nsamples += 1
            
            assert(nsamples == 1)


    def test_reset(self):
        with tempfile.TemporaryDirectory() as dirpath:
            store, ds_id, job_id, tbl_id = self.setupStore(dirpath)
            
            generator = GenCsvLikeArrow('generator',
                                        nbatches=4,
                                        table_id=tbl_id, num_rwows=10000)
            generator.gate.meta.parentset_id = ds_id
            generator.gate.meta.job_id = str(job_id)
            generator.gate.store = store
            generator.initialize()
            nbatch = 0
            for batch in generator:
                nbatch += 1
            
            generator.reset()
            for batch in generator:
                nbatch += 1
            
            self.assertEquals(nbatch, 8)
            
            #generator.reset()
            #generator.write()
            #generator = FileGenerator('test', path=dirpath, glob='*.csv')
            #batches = 0
            #for item in generator:
            #    batches += 1
            #generator.reset()
            #for item in generator:
            #    batches += 1

            #self.assertEquals(batches, 24)


if __name__ == "__main__":
    unittest.main()
#    test = GeneratorTestCase()
#    test.test_filegenerator()


