# TraceAnalyzer
Python based CSV and plain text trace readers

This application provides two main classes and companion config files:

trace_analyzer.py
- Class: TraceReaderCSV
 - Config file: TraceReaderCSV - Test fields.txt

- Class: TraceReaderPlain:
 - Config file: TraceReaderPlain - config file.txt

Application constants are defined in:

trace_analyzer_constants.py

Unit testing is possible via:

trace_analyzer_tests.py
TraceReaderCSV - Test fields.txt
TraceReaderPlain - config empty file.txt
TraceReaderPlain - config file.txt
TraceReaderPlain - one line config file.txt
TraceReaderPlain - one trigger and line config file.txt
TraceReaderPlain - one trigger config file.txt
TraceReaderPlain - test config file.txt
TraceReaderPlain - truncated section config file.txt
TraceReaderPlain - truncated trigger config file.txt
TraceReaderPlain - two trigger config file.txt
