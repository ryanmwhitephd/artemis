---
title: STC Artemis Project Conceptual Design Report
date: "December 2018"
author: "Statistics Canada, Data Stewardship Division; Ryan M. White; Dominic Parent"
---

# Artemis Conceptual Design Report
The conceptual design report describes the Artemis data processing framework
powered by Apache Arrow, an industry standard in-memory columnar data format.
The conceptual design derives from experience prototyping typical data
processing stages with Apache Arrow, aligning closely with the developments of
the Apache Arrow project, and employing data processing techniques used in the
production of large-scale scientific data sets.

## Table of Contents
1. [Introduction](#intro)
2. [Data processing requirements](#reqs)
3. [Apache Arrow](#arrow)
4. [Artemis](#artemis)
    * [Overview](#artemissummary)
    * [Business Process Model](#bpm)
    * [Execution Engine & Inter-algorithm communication](#steering)
    * [Metadata Model](#metadata)
    * [IO](#io)
    * [Data conversion](#conversion)
    * [Data Quality](#dataqual)
    * [Services, Algorithms and Tools](#services)
5. [Computing Infrastructure](#infra)
6. [Development Strategy](#devstrategy)
7. [Business IT Analytics](#it)
8. [Appendix](#appendix)

## Introduction <a name="intro"></a>

Statistical organizations are shifting to an administrative data first approach
for producing official statistics. The production of high-quality, fit-for-use
administrative data must preserve the raw state of the data throughout the data
life cycle (ingestion, integration, management, processing and analysis). Data
formats and production frameworks must support changes to analytical workloads
which have different data access patterns than traditional survey data,
efficient iteration on the data at any stage in the data cycle, and
statistical tools for continuous data quality and fit-for-use assessment.
The framework design must have at the core a well-defined data format
that can accelerate analytical processing of the data on modern computing
architecture.

At the core of any data enterprise is a consistent, well-defined data model. 
The data model will underpin the long-term data management strategy and provide
the requirements for computing, storage, and data analysis. The choice of
the data model must reflect the analysis patterns of the end-user, and
support the analytical workloads for data production. 

The Artemis data processing framework demonstrates the use of the Apache Arrow
in-memory columnar data format and modern computing techniques for data ingestion,
management and analysis of very large datasets. The framework
supports analytical workloads for administrative data sources that follow
a pattern of write once, read many times, and analytical queries with
common data access patterns based on a tabular data structure.  

The Artemis prototype leverages Apache Arrow from the start, working with Arrow
buffers to produce high-quality datasets. Artemis accomplishes this by
providing a framework to execute operations on Arrow tables (an execution
engine) through user-defined algorithms and tools. Artemis core
functionality is configurable control flow for producing datasets
consisting of one or more Arrow Tables. The language-neutral Arrow data format
allows Artemis to pass data to/from other processes or libraries, in-memory, with
zero-copy and no serialization overhead. 

The primary objectives for the prototype:

1. Production of logical datasets of a single
consistent data format that enable efficient interactions with very large
datasets in a single-node, multicore environment.
2. Support analysis on streams of record batches that do not neccesarily reside entirely in-memory.
3. Execution of complex business processes on record batches to transform data.
4. Incorporate data quality and fitness-for-use tools as part of the data production process.

The document is organized as follows:
* General requirements for data processing of administrative data (or any non-survey large datasets).
* Description of the Apache Arrow data format and development roadmap.
* Overview of the Artemis framework and detailed description of the various framework components.
* Summary

The appendix includes more detailed information and topics that require more
research and development. Such topics include different various computing
models (cloud, HPC, multiprocessing), different storage mechanisms
(distributed, local, cloud object storage), as well as communication protocols
for data management on large federated networks.  Throughout the document we
refer to current and planned developments in Apache Arrow as well as
contributions to Apache Arrow that may be incorporated into Artemis.

## General requirements for data processing <a name="reqs"></a>

In general, analyst require only a few data functions: discover, access,
process, analyze, and persist.  More comprehensively, the general
requirements for data processing and analysis consist of:

* Comprehensive, robust support for reading and writing a variety of common storage formats 
in cloud, on-premise, local or distributed data warehousing (CSV, JSON, Parquet, legacy data). 
* Ability to perform schema-on-read either through supplied schema or through type-inference 
and produce a well-defined schema for the dataset.
* Ability to extract meta-data and catalogue data sets in a language and application agnostic manner.
* Support for a write-once, read-many times iterative analysis with minimal data conversions, IO and serialization overhead.
* Effective and efficient data management.
* Efficient filtering of data, e.g. selection of columns from a master dataset.
* Perform analytical operations, e.g. projections, filters, aggregations, and joins.
* Collection of dataset statistics, e.g. marginal distributions, mean, minimum, maximum.

The design of data production frameworks, which supports the end-user analyst needs,
must focus on four key features: 

**Performance** – The typical performance indicator is the turnaround time
required to run the entire processing chain when new requirements or data are
introduced.  Runtime is limited by transfer of data, loading of data between
successive stages (or even succesive pipelines), and conversion between various
formats to be used across fragmented systems. The software must minimize the
number of read/write operations on data and process as much in memory as
possible. Distinct stages should be modular, such that changes in stages can be
rerun quickly.

**Maintainability** – Modular software with a clear separation between
algorithmic code and configuration facilitate introduction of new code which
can be integrated without affecting existing processes through configuration.
Modular code also enforces code structure and encourages re-use. Common data
format separates the I/O and deserialization from the algorithmic code, and
provide computing recipes and boiler-plate code structure to introduce new
processes into the system.

**Reliability** – The system is built on well-maintained, open-source libraries
with design features to easily introduce existing libraries for common analysis
routines. 

**Flexibility** – Re-use of common processes is faciliated through configurable algorithmic code. 
Use of a common in-memory data format simplify introducing new features, quantities and data structures
into the datasets.

## Apache Arrow industry-standard columnar data <a name="arrow"></a>

Open standards enable systems, processes and libraries to communicate with each
other.  Direct communication using standard protocols and data formats
simplifies system architecture, reduces ecosystem fragmentation, improves
interoperability across processes, and eliminates dependency on proprietary
systems.  Most importantly, common data formats facilitate code reuse, sharing,
effective collaboration and data exchange, resulting in algorithms and
libraries which are supported by a large open community.  Common data
format that defines the data primitive types that occur in data science,
social science and business data will ensure that the raw state of the data
can be preserved when consumed by organizations.  Tabular data organized in
a columnar memory layout allows applications to avoid uneccesary IO and
accelerates analytical processing on modern CPUs and GPUs. (Additional discussion
on open data standards can be found in the [Appendix](#appendix)).

The data science and social science community typically deal with tabular data
which manifests itself in various forms, most commonly refered to as
*DataFrames*. The *DataFrame* concept and the semantics found in various
systems are common to the various *DataFrames*.  However, the underlying
byte-level memory representation  varies across systems. The difference in the
in-memory representation prevents sharing of algorithmic code across various
systems and programming languages. No standard exists for in-memory tabular
data, however, tabular data is ubiquitous.  Tabular data is commonly found in
SQL, the "Big Data" community developed Spark and Hive, and in-memory
*DataFrames* are found across popular data science languages.  R, python and
Julia all have a *DataFrame* in-memory tabular data which is commonly used by
analysts.

The Apache Arrow project solves the non-portable *DataFrame* problem by
providing a cross-language development platform for in-memory data which
specifies a standardized language-independent columnar memory format for flat
and hierarchical data, organized for efficient analytic operations on modern
hardware. Arrow provides computational libraries and zero-copy streaming
messaging and interprocess communication. Arrow is a common data interface
for interprocess and remote processes.

The key benefits of Arrow:

**Fast** – enables execution engines to take advantage of the latest SIMD (Single
input multiple data) operations in modern processors, for native
vectorized optimization of analytical data processing. Columnar layout is
optimized for data locality for better performance.  The Arrow format supports
zero-copy reads for fast data access without serialization overhead.

![Arrow SIMD](docs/simd.png)

**Flexible** – Arrow acts as a high performance interface between various systems
and supports a wide variety of industry specific languages, including native
implementations in C++, Java, Javascript, Rust and Go, with bindings from C++ libraries
for Python, Ruby, and R.  

**Standard** – Apache Arrow is backed by key developers from 13 major open-source
projects, scientists working at the data frontier, deep learning, and GPU-based
software developers, including Calcite, Cassandra, Drill, Hadoop, HBase, Ibis,
Impala, Kudu, Pandas, Parquet, Phoenix, Spark, and Storm and CERN
making it the de-facto standard for columnar in-memory analytics.

![Arrow support](docs/arrow_impl.png)

Apache Arrow comprehensive data format defines primitive data types for
scalars of fixed and variable length size as well as complex types such as
unions (dense and sparse), structs and lists. Variable width data supports 
UTF8 or varchar as well as varbinary. Complex types can support nested
hierarchical data, for example, to represent nested JSON data. 

* Fixed-length supported primitive types: numbers, booleans, date and times, fixed size binary, decimals, and other values that fit into a given number
* Variable-length supported primitive types: binary, string
* Nested types: list, struct, and union
* Dictionary type: An encoded categorical type

![Arrow Buffers](docs/ArrowColumns.png)

The Arrow column-oriented in-memory format provides
serialization/deserialization and supports persistency to various
column-oriented backend storage systems and formats. The choice for
column-oriented format is based on the benefits achieved for performance
reasons.

* Common access patterns that benefit from column-oriented data access
    * Access elements in adjacent columns in succession.
    * Efficient access to specific columns.
* Enables SIMD (Single instruction multiple data) based algorithms
* Vectorized algorithms
* Columnar compression

The Apache Arrow objective is to provide a
development platform for data science systems which decouples the vertical
integration of data processing components: performant 
serialization / deserialization and I/O, standard in-memory
storage, and embedded computational engine. Apache Arrow deconstructs the typical
data architecture stack that is vertically integrated, providing public APIs
for each component. API support is focused at the developer level in order 
to avoid placing constraints in the use of the library. As algebraic operators
and embedded query engines are developed within Arrow, high-level front-end APIs
will become available to serve the average end-user (targeting users of the pandas
library, for example).

![Arrow Shared](docs/arrow-shared.png)
![Arrow Copy](docs/arrow-copy.png)

### Apache Arrow Roadmap

The following information was obtained from the 2019 Ursa Labs Planning document.
The developments listed below are the most relevant to the design
strategy for Artemis and the requirements that the prototype aims to meet. Several
planned developments are already part of the Artemis functionality, and the design
supports integration of future Arrow developments such as operators and an embedded 
query engine.

* The highest level goal of Apache Arrow is to enable efficient interactions with
very large datasets in a single node, multicore environment. 
In particular, to create libraries that can be used both for out-of-core
computing as well as distributed in-memory computing. 

* Anticipate a common workload is to perform computation on streams of record batches. 
It is not safe to assume that computation will be performed against fully in-memory or
memory-mapped datasets at all times.  
For example, it is possible to perform
many kinds of filter-project-aggregate on a very large dataset where 
only one small row batch at a time is in-memory. 

* Support to read and write complex datasets in a variety of different storage schemes.
This should not be coupled to a particular metadata storage format, like the
Hive metastore.  Some critical operations on datasets are:
  * Streaming read (one record batch at a time), either all columns or a subset of columns
  * Streaming read with predicate pushdown (filtering)
  * Infer and attempt to normalize schema (for datasets where the schema is not yet known)
  * Build new on-disk dataset given a stream of record batches

* Developers of TensorFlow learned the hard way, users wish to be able
to evaluate operators both eagerly and in deferred fashion. 
Arrow development should focus on providing as many operators as possible available
to run eagerly, in addition to building operator graphs to evaluate more
efficiently using a physical query planner.

* Provide a single-node embedded query engine that does
not have a dependency on some external or third party scheduler. 
In particular, this embedded engine could be used in-process in many
programming languages (like Python, R, Ruby) or accessed through an RPC layer.

* A particular dataset may need to be materialized in a process where there is
insufficient RAM available to hold it in memory. 
Develop tools to "spill" datasets to disk
using the Arrow binary IPC protocols (either for stream-based access or random access).

## Artemis Prototype <a name="artemis"></a>

The Artemis prototype framework leverages the Apache Arrow development platform
capability, and focuses on data processing and analysis in a
collaborative and reproducible manner.  The front-end agnostic Arrow API allows
us to define a data model to manage the sharing of tabular data across
sequences of algorithms, which describe various (sometimes disparate) business
processes in a single, in-memory, data processing job. The algorithms describe
various business processes for the same dataset, and the
algorithms can be re-used for different datasets with common pre-processing and
processing requirements.

Assumptions set forth for Artemis are derived from event-based data processing
frameworks from high-energy physics. Therefore, many design choices have been
adopted from large-scale data processing systems used in the HEP community,
which until recently, have been able to scale to the processing 
Petabytes of data per year.

### Overview <a name="artemissummary"></a>

Artemis framework design features

* Metadata management - seperation of algorithmic code and configuration.
* Performance - seperation of I/O from data processing managed at the framework level to minimize read/write. 
* Reliability - State machine for job control flow and global steering of data pipeline algorithms.
* Reproduciblity - in-memory provenance of data transformations.
* Flexibility - modular code design to faciliate code re-use, simplify testing and development.
* Automation - automatic collection of processing metrics.
* Configuration - user-defined histograms and data tables.

Artemis framework defines a common set of base classes for user defined
*Chains*, representing business processes, as an ordered collection of
algorithms and tools which transform data. User-defined algorithms inherit
methods which are invoked by the Artemis application, such that the *Chains*
are managed by a *Steering* algorithm (which also inherits from a common base
algorithm class).  Artemis manages the data processing *Event Loop*,
provides data to the algorithms, and handles data serialization and job
finalization.

![Artemis Control Flow](docs/ArtemisControlFlow.png)

The Artemis primary objective is the production of datasets which utilize
memory and cpu resources efficiently to accelerate analytical processing of
data on a single-node, multi-core machine.  The data processing can be
replicated on independent parts of the dataset in parallel across multiple
cores and / or across multiple nodes of a computing cluster in a batch-oriented
fashion.  The resulting dataset consists of a collection of output file(s),
each file is organized as a collection of record batches
(Arrow::RecordBatch). Each record batch consists of the same number of
records in each batch with a fixed, equivalent schema. The resulting file
can be considered as a table (Arrow::Table).  Note, Arrow Tables can
support nested, hierarchal tables. In the current prototype, Artemis focuses on
demonstrating the use case for flat tables.

The primary assumption for Artemis data production is that chunks
of raw data can be read into Arrow buffers and subsequently perform computation on streams 
of record batches. The computations may perform many kinds of filter-projection-aggregate
operations on very large dataset with only a small record batch in-memory. The processing
of the record batches can be parallized across many cores or across a cluster of
machines, resulting in both vertical and horizontal scaling of computing resources.

The raw dataset consists of one or more datums, such as files, database tables,
or any data partition.  In order to organize the data into collections of a
fixed number of record batches to manage the data in-memory, each datum is
separated into chunks of fixed size in bytes. Each chunk is converted from the
raw input data to a record batch. The record batch can
undergo any number of operations, e.g. parsing, conversion, cleaning,
filtering, aggregation, and integration until the the entire transformation is
applied to a record batch.  The output record batch from a raw input chunk of a
datum is written (serialized) to an output buffer (Arrow::BufferOutputStream). Raw input
data chunks continue to stream into Artemis while the record batches continue to be
serialized into the output stream. Once the buffer output stream consumes
enough memory, the output buffer is "spilled" to disk.  As more data continues
to stream into the application, new buffers are created until all files from
the raw dataset are stored in collections of Arrow record batches. 

The output dataset does not assume to map directly back to the input
dataset, as the data is reorganized into record batches to provide performant,
random access data files. The ability to transform the data in-memory
can result in one or more final output partitioning schemes which conform
to the requirements of the downstream analysis. The columnar data structure 
is highly compressible and retains the schema as well as the entire payload 
in a given file. Arrow supports both streams and random access reads, as well
as support for writing to variety of on-disk persistent storage formats, e.g. Parquet,
ORC, and Feather. Artemis utilizes the ability to "spill" to disk in configurable
file sizes into a native Arrow bytestream format. 

### Business process model <a name="bpm"></a>

Artemis design decouples the definition of the business process model, *BPM*, from
the execution of those business processes on the data. Business process models
are defined by the user and retained in the Artemis metadata. The flexibility of
defining, retaining and storing the *BPM* in the metadata enables
various configurations to be used on the same data, allows for the job to be
reproducible, and facilitates data validation and code testing.

The *BPM* can be expressed as a directed graph, describing the
relationship between data, their dependencies, and the processes to be applied
to the data. The user defines the input(s), the output, the process to be applied to 
the input(s), and the algorithms which consistute a distinct business process.
Each business process consumes data and produces new data, where
the new data is the output of one or several algorithms which transform the
data. Once the business processes are expressed in a series of algorithms, 
the processes must be transformed from a directed graph to a linear ordering
of processes (where each process is a list of algorithms using a common input).
The ordering of algorithms must ensure that the data dependencies are met
before the execution of an algorithm. 

**TODO**

Diagram Business Process Model

The ordering of the algorithmic execution is handled through a sorting
algorithm. Users only need to ensure their pipeline defines the input(s), the
sequence of algorithms to act on those inputs, and the output. The directed
graph of data relationships, *Tree*, and the execution order is defined in the Artemis
metadata.  

**Definitions**

* *Sequence* - Tuple of algorithms (by name) which must be executed in the
order defined.  
* *Node* - Name of an output business process. (COMMENT: We
need to standardize/figure out our naming scheme. Node replaces Element in our menu definition.
Also, if an Element is the output of a business process, we should state here
what is the business process.)
* *Chain* - Unordered list of input Elements (by name), a Sequence, and a
single output Element.  
* *Menu* - Collection of user-defined Chains to be
processed on a particular dataset.  
* *Tree* - Resulting directed graph data structure from the *Menu*

Artemis application requires the topological sorted list of output *Nodes* and
*Sequences*. The topological sort of a directed graph is a linear ordering of the
vertices such that for every directed edge *uv* from vertex *u* to vertex *v*,
*u* comes before *v* in the ordering. Artemis uses the python library
*toposort* to create the ordered list.  (For more information, please
refer to the Wikipedia description of topological sorting and
the toposort algorithm available on BitBucket.) The resulting *Tree*
and execution order is stored in metadata to be made available to *Artemis*.

### Execution Engine and Inter-algorithm communication <a name="steering"></a>

Artemis provides access to data from different sources. The data is read into
native Arrow buffers directly and all processing is performed on these buffers.
The in-memory native Arrow buffers are collected and organized as collections
of record batches in order to build new on-disk datasets given the stream of record batches.
Once raw data is materialized as Arrow record batches, Artemis needs to provide 
the correct data inputs to the algorithms so that the final record batches
have the defined *BPM* applied to the data.

*Artemis* has a top-level algorithm, *Steering*, which serves as the execution
engine for the user-defined algorithms.  The *Steering* algorithm manages the
data dependencies for the execution of the *BPM* by seeding the required data
inputs to each *Node* in a *Tree* via an *Element*.  The *Tree* data structure
is the directed graph generated from the user-defined *BPM Menu*.  *Steering*
holds and manages the entire *Tree* data structure, consisting of the
*Elements* of each *Node*, the relationships betweens *Nodes*, and all Arrow
buffers attached to the *Elements* (a reference to the Arrow buffers). The
*Elements* serve as a medium for inter-algorithm communication. The Arrow
buffers (data tables) are attached to *Elements* and can be accessed by
subsequent algorithms. 

**TODO**

Diagram Data Access via Elements

An interesting comparison with the Gandiva contribution to Arrow from Dremio
elucidates some parallels to Artemis.  Gandiva is a C++ library for efficient
evaluation of arbitrary SQL expressions on Arrow buffers using runtime code
generation in LLVM. Gandiva is an indepdent kernel, so in principle could be
incorporated into any analytics systems.  The application submits an expression
tree to the compiler, built in a language agnostic protobuf-based expression
representation.  Once python bindings are developed for Gandiva expressions,
Artemis could embed the expressions directly in the algorithm configuration.

Planned developments in Arrow also extend to both algebra operators as well as
an embeddable C++ execution engine.  The embedded executor engine
could be used in-process in many programming languages and therefore easily
incorporated into Artemis. Arrow developers are taking inspiration
from ideas presented in the Volcano engine and from the Ibis project.

### Metadata model <a name="metadata"></a>

The Artemis metadata model has three primary components:

1. The defintion of the data processing job, i.e. all the required metadata to execute a business process model.
    * Defintion of the data source or source(s)
    * Definition of business process model for that particular data source(s)
    * The configuration of algorithms, tools, and services required to execute the business process model
2. Job processing metadata, i.e. metadata required to support the execution of the BPM and to retain data provenance.
    * The current state of the job
    * Metadata related to the raw data source
    * Metadata associating raw input data, intermediate data and output data (provenance)
3. Summary metadata
    * Statistical information gathered during the processing of the data
    * Cost information (timing disrtibutions) for processing stages, algorithm and tool execution

Detailed information on the model can be found in the [Appendix](#appendix).

### I/O <a name="io"></a>

Artemis must support for reading and writing common data formats as well
as the legacy data formats (e.g. EBCDICs) which can be done efficiently with
different file storage systems, including cloud and distributed HPC storage
(e.g. GlusterFS). 

Arrow is focused on interactions of 5 primary storage formats: CSV, JSON,
Parquet, Avro, and ORC. A single file in any of these formats can define
a single tabular dataset, or many files together forming a multi-file dataset.
Arrow provides I/O capability for local disk, shared memory and in-memory
storage. Plans for development for interfacing with cloud-based storage is
anticipated. Some development for interacting the hdfs was provided by the Dask
developers.

Artemis uses the Arrow native file type handles (e.g. NativeFile, Buffer,
OSFile) for reading / writing to local disk for both the raw data as
well the converted Arrow tabular data. Artemis also uses the Arrow
BufferOutputStream for managing data for writing out random access files.  

Artemis will be able to leverage planned developments for dataset abstraction,
since datasets will already be organized in a logical set of files
consisting of record batches. This will enable dataset functionality
for
    
* Streaming read (onme record at a time), either on columns or subsets of coumns
* Streaming read with filtering (predicate filtering)
* Constructing new on-disk datasets given a stream of record batches

Ideally, once the raw data is organized into Arrow tabular datasets, simple,
high-level code for skimming data (selecting) columns and slimming data
(predicate pushdown) can be easily implemented to run over datums in
parallel (one-job per file). See the [Appendix](#appendix) for more discussion.

Modularity of I/O can allow for a seperate process entirely to serve data to
the application. Arrow developments for I/O tools, performant database
connectors, and messaging are on the roadmap, and Artemis must be able to
easily leverage these capabilities as they become available.

### Data conversion <a name="conversion"></a> 

For each data format, Artemis and Arrow aim to support some rudimentary features

* Convert from Arrow record batches to the target format, and back, with minimal loss.
* Automatic decompression of input files.
* Given a supplied schema, read a file in one chunk at time.
* Schema inference (schema on read)
* Conversion profiling for converted data, e.g. frequencies of errors in columns for converting to the desired data type

Artemis works with the schema-on-read paradigm, a general requirement for data
science applications. Artemis manages the creation and reading of raw data
chunks, in addition to fetching the schema (if available) from the input datum.
(A predefined schema can also be provided as part of the initial Artemis job configuration.)
Artemis passes the raw data chunk to the Arrow readers for column-wise type
inference and data conversion to an Arrow record batch. Robust checking of the
supplied and/or extracted schema against the inferred data types occurs on each
chunk. Artemis also collects statistics on errors occured during processing,
recording this information in frequency tables or histograms as part of the
job summary metadata.  The data error handling and statistics rely on
information gathered from the Arrow readers.

Arrow provides funtionality to chunk data in their readers, returning an Arrow
table of one or more record batches. However, delegating this funtionality to
Artemis allows the framework to configure the size of the raw data to process
in memory, apply all downstream processes to the data one chunk at a time a
time, monitor the total Arrow memory consumption and handle flushing the Arrow
memory and "spilling" processed data to disk.

The Artemis algorithms leverage the functionality of Arrow by directly interacting with
Arrow record batches. Arrow parsers are implemented to support both
single-threaded and multi-threaded reads, adapting the Artemis data chunker on
the Arrow implementation could be a foreseen development. As well, Artemis is
targeting the processing of legacy data (from mainframe, Cobol applications).
Developing a native Arrow reader for EBCDIC data format in C++ could be
considered a worthwhile contribution to the Arrow project.

Refer to the [Appendix](#appendix) for additional details of the CSV reader implemented in Arrow.

### Data quality <a name="dataqual"></a>

The data quality is an inherent part of data analysis, and therefore needs
to be part of the core design of Artemis.
The importance of data quality transcends domains of science, engineering,
commerce, medicine, public health and policy.  Traditionally, data quality can be
addressed by controlling the measurement and data collection processes and
through data ownershp. The increased use of administrative data sources
poses a challenge on both ownership and controls of the data. Data quality
tools, techniques and methodologies will need to evolve. 

In the scientific domain, data quality is generally considered an implicit part
of the role of the data user.  Statistical infrastructure will need support the
data users ability to measure data quality throughout the data lifecycle.
Data-as-a-service oriented enterpise data solutions are not generally focused
on ensuring the measurement of data quality. As well, the statistical tools
required for data quality meaurements need to be developed to address data quality
issues in administrative data. Artemis primary statistical analysis tool for
data quality is the histogram.

Histograms are the bread-and-butter of statistical data
analysis and data visualization, and a key tool for quality control. They
serve as an ideal statistical tool for describing data, and can be used
to summarize large datasets by retaining both the frequencies as well as the errors.
The histogram is an accurate representation of a distribution of numerical data (or
dictionary encoded categorical data), and it represents graphically the
relationship between a probability density function *f(x)* and a set of *n*
observations, *x, x1, x2, ... xn*. 

Artemis retains distributions related to the processing and overall cost
of the processing for centralized monitoring services: 

* Timing distributions for each processing stage
* Timing distributions for each algorithm in the BPM
* Payload sizes, including datums and chunks
* Memory consumption 
* Total batches processed, number of records per batch
* Statistics on processing errors

Separate histogram-based monitoring applications can be developed as a
postprocessing stage of Artemis and will be able to quickly iterate over large
datasets since the input data are Arrow record batches. Automated profiling of
the distributions of the data is forseen as well for input to the
postprocessing stage data quality algorithms. Further discussion on automated
profiling is included in the appendix.

### Services, algorithms and tools <a name="services"></a>

#### In-memory data store

The data access of Arrow buffers is facilitated by an in-memory data store.
The *Elements* available in the user-defined algorithms provide
references to the actual Arrow buffers. The data buffers
reside in a backing data store (or sink) that can be changed, under the hood,
while the interaction of retrieving and attaching data to the *Elements* remains
unchanged. The reference of the data that is retained in the *Element* is a unique
key (UUID) that can be used to retrieve the data from any backing key-value
store. The current implementation uses a python dictionary to 
manage the Arrow buffers. The Apache Ray project contributed the Plasma
shared memory object store to the Arrow project. In the case of running
Artemis on a multicore machine, multiple Artemis subprocesses could 
write to a single Plasma object store and faciliate asyncronous 
collections of Arrow record batches to write to disk. A shared object store
may also faciliate shuffling of data across large data sets as well. 

The advantage of the abstraction of data access via the dependecy *Tree* from 
the underlying data store simplifies data access for user-defined algorithms;
allows for the framework to manage the memory; provides control for spilling data 
to disk when needed and flushing the memory; enables the use of shared memory
data stores for leveraging a multicore environment; aleviating the need
for users to deal with data management, serialization and persistency. In
other words, any algorithm that works with Arrow data types can be easily 
incorporated into the Artemis framework with general ease.

#### Metastore

In order to ensure flexibility, reproducibility and to separate the definition of the BPM from
the execution, Artemis requires a metadata model with a persistent representation. The persistent, serialized
metadata must be flexible to work with, to store, and to use within Artemis and other applications. 
The Artemis metadata model must be able to support external application development and use within
a scalable data production infrastructure.

Artemis metadata model is defined in a google protobuf messaging format. 
Protocol buffers are language-neutral, platform-neutral, extensible mechanism for serializing
structured data – think XML, but smaller, faster, and simpler. Protocol buffers
were developed by Google to support their infrastructure for service and application communication.
Protobuf message format enables Artemis to define how to stucture metadata once, then special 
source code is generated to easily write and read the structured metadata to and from a variety
of data streams and using a variety of languages. (Google developor pages). Protobuf messages
can be read with reflection without a schema, making the format extremely flexible in terms
of application development, use and persistency. 

The serialized protobuf is a bytestring, in other words a BLOB (binary large
object), which is a flexible, lightweight storage mechanism for
metadata. The language-neutral message format implies that any application can
be built to interact with the data, while the BLOB simplifies storage. The
messages can be persisted simply as files on a local filesystem, or for
improved metadata management the messages can be cataloged in a simple
key-value store. Applications can persist and retrieve configurations using a
key. 

**TODO**

Diagram for simple KV store and artemis

The idea of persisting the configuration as well as managing the state of
Artemis derived from experimentation with the Pachyderm data science workflow
tool and Kubernetes. Moreover, Arrow intends to develop secure, over the wire
message transport layer in the Arrow Flight project using gRPC and protobuf.
Artemis can leverage Arrow Flight along with gRPC to build scalable, secure,
data processing architecture that can be flexible for cloud-native and 
HPC deployments.

#### Histogram and Timer Store

Histograms and timers are centralled managed by the framework.  The managed
store allow Artemis to collect histograms and timing information into the
metadata, serialize and persist this information at the job finalize stage. The
stores support booking and filling histograms in any user-defined algorithms. 

The histogram store also works as proxy to different histogram representations. Artemis
currrently support two libraries histbook (from diana-hep) and physt (janpipek). Use
in Artemis is primarily with physt since conversion to and from protobuf is supported.
Once the physt histogram is converted to a protobuf message, the collection is added
to the job metastore. 

#### Algorithms and Tools

Similar to the idea of *numpy* user-defined functions, Artemis supports
user-defined algorithms and tools.  Any algorithm or tool which works with
Arrow data structures can be easily incorporated into an Artemis *BPM* and
executed on a dataset. Algorithms support user-defined properties in order to
easily re-use algorithmic code to perform the same task with different
configurations.  Developers implement the base class methods, define any
defined properties, and access the Arrow buffers through the *Element*.
*Steering* manages algorithm instantiation, scheduling and execution.  For the
end-user the most important part of the code is defined in the ```execute```
method.  Code organization and re-use can be improved by delegating common
tasks which return a value to tools.  The scheduling of the tools is managed
directly in the algorithm, in other words, it is up to the user to apply the
tools in the appropiate order.

```python
class MyAlgo(AlgoBase):
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        # kwargs are the user-defined properties
        # defined at configuration 
    def initialize(self):
        pass
    def book(self):
        # define histograms and timers
    def execute(self, element):
        # Algorithmic code
    def finalize(self):
        # gather any user-defined summary information
```

#### Logging and exception handling

Artemis uses standard python logging module as well as exception handling.
The framework provides a logging functionality with a decorator. All algorithms can access
a logger, using ```self.__logger.info("My message")```. 

Exceptions must be raised in order to propagate upward. As long as all
exceptions can be handled appropiately, the framework gracefully moves into an
**Abort** state if the exception prevents further processing. 

## Summary

Statistical organizations are shifting to an administrative data first approach
for producing official statistics. Inherent in the production of high-quality,
fit-for-use administrative data is the ability for analysts to use the data,
measure data quality, and iteratively develop data applications and
statistical tools. Administrative datasets are becoming increasingly larger
and complex, challenging the ways we approach data analysis and computing.
The Apache Arrow in-memory columnar data format provides the ability to
develop statistical infrastructure to address data quality and fit-for-use
challenges with adminstrative data; better define computing requirements with the
efficient use of CPU and memory; build sustainable, secure and coherent data ecosystems
with interoperability; foster a collaborative environment due to code re-use.
The Artemis data processing framework demonstrates the ease to design, build
and scale data science systems using a single, open source library to deliver high-quality,
manageable data sets designed for efficient processing on single-node, multicore environments.

## References <a name="refs"></a>

* Canonical Apache Arrow source code, https://github.com/apache/arrow 
* Wes McKinney, 2019 Ursa Labs Planning Document, https://docs.google.com/document/d/12dWBniKW2JQ-5djE3SPjyQXVquCAEmLXVlb1dnhLhQ0/edit#heading=h.62rx18p423rw
* Apache Arrow homepage: http://arrow.apache.org
* Apache Arrow columnar format specification, https://cwiki.apache.org/confluence/display/ARROW/Columnar+Format+1.0+Milestone)
* Atlas Collaboration, ATLAS high-level trigger, data-acquisition and controls: 
Technical Design Report, CERN-LHCC-2003-022; ATLAS-TDR-16
* Google Protocol Buffers, github.com/protocolbuffers/protobuf, developers.google.com/protocol-buffers/
* The NumPy array: a structure for efficient numerical computation, 
Van Der Walt, Stefan; Colbert, S. Chris; Varoquaux, Gael,
Computing in Science and Engineering 13, 2 (2011) 22-30, 2011
* Graefe, Goetz, "Volcano, an Extensible and Parallel Query Evaluation System"; 
CU-CS-481-90 (1990). Computer Science Technical Reports, 463 
https://scholar.colorado.edu/csci_techreports/463
* Gandiva initiative for Apache Arrow, https://www.dremio.com/announcing-gandiva-initiative-for-apache-arrow)
* Ibis, Python Data Analysis Productivity Framework, https://docs.ibis-project.org/html
* The Evolution of Data Quality: Understanding the Transdisciplinary Origins of Data Quality Approaches, 
S. Keller; G. Korkmaz; M. Orr; A. Schroeder; and S. Schipp, Annu. Rev. Stat Appl. 2017. 4:85-108
* Freedman, David; Diaconis, Persi (December 1981). "On the histogram as a density estimator: L2 theory", Probability Theory and Related Fields. HeidelbergL: Springer Berlin. **57**
* EOS as the present and future solution for data storage at CERN, AJ Peters; EA Sindrilaru; G Adde,
Journal of Physics, Conference Series 664 (2015) 042042
* Glen Cowan, *Statistical Data Analysis*, Oxford Press, 1998


## Appendix <a name="appendix"></a>

### Requirements for data science 

The Artemis conceptual design aims at addressing data science core requirements for performing 
rigourous data analysis. 

* Discoverability
* Reproducbility
* Provenance
* Incrementality
* Collaboration
* Accessibility & Autonomy
* Performance
* Ease of use, maintability
* Flexibility to incorporate new Arrow developments
    * Multi-language support via python 
    * Native C++ algorithms with bindings, callable R algorithms via rpy?
* Reliability

### Description of open data standards and formats

The scientific community developed many common libraries in-use by data
scientists today in Fortran, such as linear algebra routines. The scientific
programming ecosystem in python effectively united around the ndarray, which is
the NumPy multidimensional fortran-compatible array which allows for re-use of
linear algrabra routines, providing zero-overhead memory sharing to/from
various libraries and processes.
Several examples of data standards in computing today:

* Human-readable semi-structured: XML, JSON
* Structure data query lanaguage: SQL has various flavors (MySQL, PostgreSQL, etc...)
* Binary data (with metadata), several from the scientific community
    * NetCDF
    * HDF5
    * Apache Parquet, ORC
    * PAW tuples and ROOT TTree 
* Binary blobs via RPC protocols
    * Apache Avro
    * Protocol buffers (Google)
    
### Artemis Metadata model

* Job Configuration
  * Data source(s)
  * Execution graph 
  * Data dependency tree
  * User-defined algorithm and tool configuration
* Job Process
  * Job state
  * Data source information
    * Metadata, i.e. schema
    * Datum payload size
    * Chunk payload size
* Statistics
  * Histograms
  * Timers
  * Job summary

### Reading CSV Files with Arrow

Arrow provides support for reading data from CSV files with the following features:

* multi-threaded or single-threaded reading
* automatic decompression of input files (based on the filename extension)
* fetching column names from the first row in the CSV file
* column-wise type inference and conversion to one of null, int64, float64,timestamp[s],
string, or binary data
* detect various spellings of null values (sentinel values) such as NaN or #N/A

### Profiling techniques for large datasets

Automated data profiling can be a powerful tool for data quality, data discovery,
and fit-for-use assessment. However, unless the distributions are well-understood, such as
the resolution on the measurement and expected limits on the distribution, quickly
profiling data can be challening. For distributed processing of data, unless the histogram
definition (bin width, number of bins and limits) is fixed, the histograms for each datum
cannot be merged. In addition, the number of processing stages needs to be minimized while
still gathering relevant information on the entire dataset.

Statistical approaches, such as the Friedman-Diaconis rule for determining
optimal bin width of histograms can be used as part of the initial data quality
and profiling of new datasets. For automated profiling, sufficient information
needs to be gathered from an initial pass over the data in order to calculate
the bin width, e.g. total number of observations and interquartile range (IQR).
If the data is processed in a distributed manner, the differences in the
interquartile range from different data partitions would need to be reconciled. 

### Data Production

High-level summary of techniques for efficient data production with Arrow columnar 
data. The following processing capabilities can be used either within Artemis or
standalone applications can be developed using Arrow. 

* Scalable batch processing
* Efficient skimming (selection of column subsets)
* Efficient filtering (selection of column and row subsets from fast queries)
* Postprocessing and dataset merging

### Synthetic Information Technology

The development of synthetic information technology is inherently part of the Artemis project.
In order to adequately test code, validate data processing, and ensure reproducibility,
data generators are required. The use of simulated data is more cost effective and
far safer than using real data. Large-scale testing of distributed processes can be initially
done using simulated data. 

Data generators for application development focus on high-quality synthetic data for
following purposes (and priorities in terms of development):

* Structural data format, e.g. csv, ebcdic, etc.
* Primitive data types
* Database generators, e.g. hierarchical databases.
* Complex data types, e.g. hierarchical JSON schemas supporting sparse unions of lists.
* Fake data of common fields encountered in social science, e.g. social security number, timestamps, banking information, etc..
* Sampling from probility distribution function (single or multidimensional)

For use in developing embeddable query engines, for instance. See Arrow-3998 and TPC-H dbgen.

### Computing infrastructure recommendations <a name="infra"></a>

* Advantageous use of cloud for simulation / data synthesis
* Secure HPC environment for SSI analysis
* Analyst challenges for migrating to HPC environment
* Dataset management

Large-scale distibuted dataset management is a critical computing requirement for
data frontier scientific experiments. The design of of both storage 
and data transport protocols is based on the general requirements of the science
use-cases. CERN developed an open source storage system that meets the needs of
the experiments and provided integration with the protocol mechanism for
transporting petabyte-scale dataset across the globe. Strategies for cloud or
hybrid cloud pose challenges, as the underlying storage mechanisms may lead 
to different latencies which would need to be considered when designing 
data ingestion, processing and data production applications. 

### Development strategies <a name="devstrategy"></a>

* Dual-use development strategy for cloud-native and traditional HPC scientific computing 
* Leveraging simulation and data syntethis production for research
* Developing a secure HPC environment for near term research

### Recommendations for IT Business Data Analytics <a name="it"></a>

* Significant advantage of Arrow is the ability for data scientists to develop
directly with the Arrow API and / or
take advantage of dataframe-like semantics. This still poses a challenge for
business analysts and the IT counterpount. 

* The Big Data community is already leveraging Arrow under-the-hood to deliver
analytics tailored toward curating data 
to deliver to a wide-range of users. The Dremio project along with the Gandiva
contribution is delivering such solutions to get data to BI tools, machine
learning, SQL, and data science clients. 

* Developing a common experimental project to leverage both Dremio and Artemis
on common datasets and data problem would
better elucidate the strengths and weaknesses of out-of-box enterprise
solutions and direct data science application development. 

* Integration of GPU-based analysis workloads using Arrow tables.
