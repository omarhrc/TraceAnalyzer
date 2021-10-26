# -*- coding: utf-8 -*-
"""
Created on Tue Oct 12 12:07:24 2021

@author: orubio
"""

from trace_analyzer import TraceReaderCSV, TraceReaderPlain, Transaction
import unittest

TRACE_READER_CSV_CONFIG_FILE = 'TraceReaderCSV - Test fields.txt'
TRACE_SAMPLE_CSV = 'TraceReaderCSV - Test CSV.csv'
TRACE_SAMPLE_CSV_NUM_RECORDS = 100

# Pairs of tests, expected (transactions, sections, parameters)
TRACE_READER_PLAIN_CONFIG_TESTS = {
    'TraceReaderPlain - config empty file.txt' : (0, 0, 0),
    'TraceReaderPlain - one line config file.txt' : (0, 0, 0),
    'TraceReaderPlain - truncated trigger config file.txt' : (0, 0, 0),
    'TraceReaderPlain - truncated section config file.txt' : (1, 1, 2),
    'TraceReaderPlain - one trigger config file.txt' : (1, 2, 8),
    'TraceReaderPlain - one trigger and line config file.txt' : (1, 2, 8),
    'TraceReaderPlain - two trigger config file.txt' : (2, 4, 16)
}

TRACE_READER_PLAIN_CONFIG_FILE = 'TraceReaderPlain - test config file.txt'
TRACE_SAMPLE_PLAIN = 'TraceReaderPlain - Test trace.txt'
TRACE_SAMPLE_PLAIN_NUM_CALLS = 10
TRACE_SAMPLE_PLAIN_NUM_MESSAGES = 45

class TestTraceReaderCSV(unittest.TestCase):
    ''' TraceReaderCSV test cases '''
    def test_no_arg_constructor(self):
        self.trace_reader = TraceReaderCSV()
        self.assertEqual(self.trace_reader.get_data(), None)
        self.assertEqual(self.trace_reader.get_fields(), {})
        
    def test_read_config_file(self):
        self.trace_reader = TraceReaderCSV()
        fields_found = self.trace_reader.read_config_file(
            config_filename=TRACE_READER_CSV_CONFIG_FILE)
        print(f'Number of fields found: {fields_found}')
        print(f'Fields found: {self.trace_reader.get_fields()}')
        self.assertEqual(len(self.trace_reader.get_fields()), fields_found)
        
    def test_read_trace_file(self):
        self.trace_reader = TraceReaderCSV(
            config_filename=TRACE_READER_CSV_CONFIG_FILE,
            trace_filename=TRACE_SAMPLE_CSV)
        print(f'Calls found: {self.trace_reader.get_data()}')
        df_num_records, df_num_columns = self.trace_reader.get_data().shape
        self.assertEqual(df_num_records, TRACE_SAMPLE_CSV_NUM_RECORDS)
        fields_found = self.trace_reader.read_config_file(
            config_filename=TRACE_READER_CSV_CONFIG_FILE)
        self.assertEqual(df_num_columns, fields_found)        


class TestTraceReaderPlain(unittest.TestCase) :
    
    def setUp(self):
        self.trace_reader = TraceReaderPlain()
        
    ''' TraceReaderPlain test cases'''
    def test_no_arg_constructor(self):
        self.assertEqual(self.trace_reader.get_data(), None)
        self.assertEqual(self.trace_reader.get_fields(), {})
        
    def test_read_config_file(self):
        print(40 * '*' + '\nTesting transaction config reader')
        for config_file, expectations in TRACE_READER_PLAIN_CONFIG_TESTS.items():
            exp_triggers, exp_sections, exp_parms = expectations
            print(f'File: {config_file}') 
            triggers_found = self.trace_reader.read_config_file(
                config_filename=config_file)
            sections_found = 0
            parameters_found = 0
            for trigger in self.trace_reader.get_triggers():
                sections_found += len(trigger.section_triggers)
                for section in trigger.section_triggers:
                    parameters_found += len(section.parameters)
            print(f'Number of triggers found: {triggers_found}')
            print(f'Number of sections found: {sections_found}')
            print(f'Number of parameters found: {parameters_found}')
            print(40 * '-')
            self.assertEqual(triggers_found, exp_triggers)
            self.assertEqual(sections_found, exp_sections)
            self.assertEqual(parameters_found, exp_parms)
        
    def test_read_trace_file(self):
        print(40 * '*' + '\nTesting transaction reader')        
        self.trace_reader = TraceReaderPlain(
            config_filename=TRACE_READER_PLAIN_CONFIG_FILE,
            trace_filename=TRACE_SAMPLE_PLAIN)
        df_result = self.trace_reader.get_data()
        print(f'Calls found: {df_result}')
        self.assertEqual(df_result.shape[0], TRACE_SAMPLE_PLAIN_NUM_MESSAGES)        

class TestTransaction(unittest.TestCase):
    
    def setUp(self):
        trace_reader = TraceReaderPlain(config_filename=
                                        TRACE_READER_PLAIN_CONFIG_FILE)
        self.triggers = trace_reader.get_triggers()
    
    def test_transaction(self):
        self.assertTrue(self.triggers)
        transaction_instance = Transaction(0, self.triggers[0])
        self.assertEqual(transaction_instance.get_trigger(), self.triggers[0])
        transaction_instance.set_field("Message #1", "A", 1)
        transaction_instance.set_field("Message #1", "B", 2)
        transaction_instance.set_field("Message #2", "B", 3)
        transaction_instance.set_field("Message #2", "C", 4)
        transaction_instance.set_field("Message #3", "D", 5)
        print(40 * '*' + '\nTesting Transaction class')        
        print(transaction_instance)
        self.assertEqual(len(transaction_instance), 3)     

    def test_to_dataframe(self):
        self.assertTrue(self.triggers)
        transaction_instance = Transaction(0, self.triggers[0])
        transaction_instance.set_field("Message #1", "A", 1)
        transaction_instance.set_field("Message #1", "B", 2)
        transaction_instance.set_field("Message #2", "B", 3)
        transaction_instance.set_field("Message #2", "C", 4)
        transaction_instance.set_field("Message #3", "D", 5)
        df = transaction_instance.to_DataFrame()
        print(40 * '*' + '\nTesting Transaction to DataFrame')        
        print(df)
        self.assertTupleEqual((3, 5), df.shape)    
 
    
unittest.main()
