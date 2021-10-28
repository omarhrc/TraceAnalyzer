# -*- coding: utf-8 -*-
"""
Created on Wed Sep 29 11:28:46 2021

@author: orubio
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import pandas as pd
import re

import trace_analyzer_constants as tac


class TraceReader(ABC):
    ''' Abstract class to define the interface to trace readers '''
    
    def __init__(self):
        self.df = None
        self.fields = {}
        
    def get_data(self):
        return self.df
    
    def get_fields(self):
        return self.fields

    def get_key_value(self, input_line, sep='\t'):
        ''' Helper function to extract key : value pairs '''
        key, value = None, None
        input_line = input_line.split(sep)
        if len(input_line) >= 2:
            key, value = [x.strip() for x in input_line][:2]
        return key, value
    
    @abstractmethod
    def read_config_file(self, config_filename, **kwargs):
        pass
    
    @abstractmethod
    def read_trace_file(self, trace_filename, **kwargs):
        pass


class TraceReaderCSV(TraceReader):
    ''' Concrete TraceReader class to read CSV trace files'''
    def __init__(self, config_filename=None,
                 trace_filename=None, sep='\t', skiprows=0):
        super().__init__()
        if not config_filename:
            return
        self.read_config_file(config_filename)
        if trace_filename:
            self.read_trace_file(trace_filename, sep=sep, skiprows=skiprows)
            
    def read_config_file(self, config_filename, sep='\t'):
        ''' Assumes each line contains a pair of Field, dtype '''
        fields_found = 0
        if not config_filename:
            raise(ValueError("Incorrect config file"))
        with open(config_filename, 'r') as f:
            input_line = f.readline()
            while (input_line):
                key, value = self.get_key_value(input_line, sep)
                if key:
                    self.fields[key] = value
                    fields_found += 1
                input_line = f.readline()
        return fields_found  
    
    def read_trace_file(self, trace_filename, sep='\t', skiprows=0):
        if not trace_filename:
            raise(ValueError("Incorrect file name"))
        non_datetime_fields = {key:value for key, value in self.fields.items() 
            if value != tac.PD_DATETIME_TYPE}
        datetime_fields = [key for key, value in self.fields.items() if value == 
                           tac.PD_DATETIME_TYPE]
        self.df = pd.read_csv(trace_filename, sep=sep, skiprows=skiprows,
                              usecols=self.fields.keys(),
                              dtype=non_datetime_fields,
                              parse_dates=datetime_fields)


class TraceReaderPlain(TraceReader):
    ''' Concrete TraceReader class to read plain text trace files'''
    def __init__(self, config_filename=None,
                 trace_filename=None):
        super().__init__()
        self.transaction_triggers = []
        if not config_filename:
            return
        self.read_config_file(config_filename)
        if trace_filename:
            self.read_trace_file(trace_filename)
            
    def read_config_file(self, config_filename, sep='\t'):
        ''' Assumptions:
            - Each transaction definition is separated by one or more empty lines
            - Quotation marks are used only for visual grouping. They are removed
        '''
        if not config_filename:
            raise(ValueError("Incorrect config file"))
        t_config_context = TransactionConfigContext()
        with open(config_filename, 'r') as f:
            input_line = f.readline()
            while (t_config_context.process_line(input_line)):
                input_line = f.readline()
            self.transaction_triggers = t_config_context.get_transaction_triggers()
        return len(self.transaction_triggers)
    
    def read_trace_file(self, trace_filename):
        if not trace_filename:
            raise(ValueError("Incorrect file name"))
        transaction_context = TransactionTraceContext(self.transaction_triggers)
        with open(trace_filename, 'r') as f:
            input_line = f.readline()
            while (transaction_context.process_line(input_line)):
                input_line = f.readline()
            self.df = transaction_context.get_result()
        return self.df.shape[0]
    
    def get_triggers(self):
        return self.transaction_triggers


@dataclass
class SectionTrigger:
    section_trigger : str = ""
    parameters : list = field(default_factory=list)
    
    def is_complete(self):
        return all(self.__dict__.values())   

        
@dataclass
class TransactionTrigger():
    ''' Data structure encapsulating a trigger definition '''
    transaction_name : str = ""
    transaction_start_trigger : str = ""
    msg_timestamp_trigger : str = ""
    msg_trigger : str = ""
    section_triggers : list = field(default_factory=list)      

    def is_complete(self):
        return all(self.__dict__.values())


class Message(dict):
    ''' Data container for a message '''
    def __init__(self, message_id):
        self.message_id = {'Message ID': message_id}
    

class Transaction(dict):
    ''' Data container for a transaction 
        It is a collection of Message objects plus control info
    '''
    def __init__(self, transaction_id, transaction_trigger):
        self.transaction_id = transaction_id
        self.transaction_trigger = transaction_trigger
    
    def get_section_triggers(self):
        return self.transaction_trigger.section_triggers 
    
    def get_trigger(self):
        return self.transaction_trigger
    
    def set_field(self, message_id, field, value):
        message = self.get(message_id, Message(message_id))
        message[field] = value
        self[message_id] = message
    
    def to_DataFrame(self):
        rows = []
        for message in self.values():
            row = {**{'TID':self.transaction_id}, **message}
            rows.append(row)
        return pd.DataFrame(rows)
    
    def __repr__(self):
        result = f'TID = {self.transaction_id}\n'
        result += super().__repr__()
        return result
        
    
class TransactionConfigContext():
    ''' Context to implement transaction config state machine '''

    def __init__(self):
        self.current_trigger = TransactionTrigger()
        self.current_section = SectionTrigger()
        # Collected triggers
        self.transaction_triggers = []
        # Machine states
        self.state_search_for_start = TransactionConfigSearchForStart(self)
        self.state_collect_parameters = TransactionConfigCollectParms(self)
        self.state_collect_section = TransactionConfigSection(self)
        # Initial state
        self.set_state(self.state_search_for_start)
        
        
    def process_line(self, input_line):
        if not input_line:
            self.next_state.eof_found()
            return False
        if input_line in ('''\r\n''', '''\n'''):
            self.next_state.empty_line()
            return True
        key, value = self.get_key_value(input_line)
        if key is None:
            return False
        self.next_state.process_line(key, value)
        return True

    def set_state(self, state):
        self.next_state = state 

    def store_update_current_trigger(self):
        self.transaction_triggers.append(self.current_trigger)
        self.current_trigger = TransactionTrigger()           

    def store_update_current_section(self):
        self.current_trigger.section_triggers.append(self.current_section)
        self.current_section = SectionTrigger() 
        
    def clear_current_section(self):
        self.current_section = SectionTrigger()

    def get_key_value(self, input_line, sep='\t'):
        ''' Helper function to extract key : value pairs '''
        key, value = None, None
        input_line = input_line.split(sep)
        if len(input_line) >= 2:
            key, value = [x.strip() for x in input_line][:2]
        if value and tac.TRANSACTION_CONFIG_REMOVE_QUOTES:
            value = value.replace('\"', '')
        return key, value   
    
    def get_transaction_triggers(self):
        return self.transaction_triggers
    

class TransactionConfigState(ABC):
    ''' Abstract class defining the interface to all transaction states '''

    def __init__(self, context):
        self.context = context
    
    @abstractmethod
    def process_line(self, input_line):
        pass

    def empty_line(self):
        self.update_all()
        self.context.set_state(self.context.state_search_for_start)
        
    def eof_found(self):
        self.update_all()
   
    def update_all(self):
        if self.context.current_section.is_complete():
            self.context.store_update_current_section()
        if self.context.current_trigger.is_complete():
            self.context.store_update_current_trigger()
            

class TransactionConfigSearchForStart(TransactionConfigState):
    ''' State: Searching for transaction start'''

    def process_line(self, key, value):
        if key == tac.TRANSACTION_NAME:
            self.context.current_trigger.transaction_name = value
            self.context.set_state(self.context.state_collect_parameters)


class TransactionConfigCollectParms(TransactionConfigState):
    ''' State: Collect transaction config parameters'''

    def process_line(self, key, value):
        if key == tac.TRANSACTION_START_TRIGGER:
            self.context.current_trigger.transaction_start_trigger = value
        if key == tac.MSG_TIMESTAMP_TRIGGER:
            self.context.current_trigger.msg_timestamp_trigger = value
        if key == tac.MSG_TRIGGER:
            self.context.current_trigger.msg_trigger = value
        if key == tac.SECTION_TRIGGER:
            self.context.current_section.section_trigger = value
            self.context.set_state(self.context.state_collect_section)

    
class TransactionConfigSection(TransactionConfigState):
    ''' State: Process section'''

    def process_line(self, key, value):
        if key == tac.SECTION_TRIGGER:
            if self.context.current_section.is_complete():
                self.context.store_update_current_section()
            else:
                self.context.clear_current_section()
            self.context.current_section.section_trigger = value
        if key == tac.SECTION_PARAM:
            self.context.current_section.parameters.append(value)

    
class TransactionTraceContext():
    ''' Context to implement transaction trace state machine '''

    def __init__(self, transaction_triggers):
        self.trigger_matches = []
        self.current_trigger = None
        self.current_section_trigger = None
        self.current_transaction_index = 0
        self.current_transaction = None
        self.empty_lines = 0
        self.df = pd.DataFrame()
        # Info to find
        self.transaction_triggers = transaction_triggers
        # Machine states
        self.state_search_for_start = TransactionTraceSearchForStart(self)
        self.state_collect_time = TransactionTraceCollectTime(self)
        self.state_start_message = TransactionTraceStartMessage(self)
        self.state_collect_section = TransactionTraceCollectSection(self)
        # Initial state
        self.set_state(self.state_search_for_start)
        
    def process_line(self, input_line):
        if not input_line:
            self.next_state.eof_found()
            return False
        if input_line in ('''\r\n''', '''\n'''):
            self.next_state.empty_line()
            return True
        self.next_state.process_line(input_line)
        return True

    def set_state(self, state):
        self.next_state = state 
   
    def get_result(self):
        return self.df
    
    def update_result(self):
        self.current_section_trigger = None
        df_current_transaction = self.current_transaction.to_DataFrame()
        if (df_current_transaction.shape[1] > 4):
            # At least one message has been added to the transaction
            self.df = self.df.append(df_current_transaction,
                                     ignore_index=True)
    
    def get_triggers(self):
        return self.transaction_triggers
        
    
class TransactionTraceState(ABC):
    ''' Abstract class defining the interface to all transaction states '''

    def __init__(self, context):
        self.context = context
    
    @abstractmethod
    def process_line(self, input_line):
        pass

    @abstractmethod
    def empty_line(self):
        pass
    
    def eof_found(self):
        self.context.update_result()
          

class TransactionTraceSearchForStart(TransactionTraceState):
    ''' State: Searching for transaction start'''

    def process_line(self, input_line):
        ''' Checks if there is matching transaction trigger. If found
            makes it the current trigger and move to next state
        '''
        transaction_triggers = self.context.get_triggers()
        trigger_matches = []
        for trigger in transaction_triggers:
            match = re.search(trigger.transaction_start_trigger,
                              input_line)
            if match:
                trigger_matches.append(trigger)
        if trigger_matches:
            self.context.trigger_matches = trigger_matches
            self.context.current_transaction_index += 1
            print(f'Transaction = {self.context.current_transaction_index}')
            self.context.current_transaction = None
            self.context.set_state(self.context.state_collect_time)


    def empty_line(self):
        ''' Keeps searching '''
        pass
    

class TransactionTraceCollectTime(TransactionTraceState):
    ''' State: Collect message timestamps'''

    def process_line(self, input_line):
        transaction = self.context.current_transaction
        if transaction:
            trigger = transaction.get_trigger()
            self.collect_info(input_line, transaction, trigger)
        else:
            for trigger in self.context.trigger_matches:
                tid = self.context.current_transaction_index    
                transaction = Transaction(tid, trigger)
                groups = self.collect_info(input_line, transaction, trigger)
                if groups:
                    # groups[2] contains the transaction type
                    if trigger.transaction_name in groups[2]:
                        self.context.current_transaction = transaction
                        break
    
    def collect_info(self, input_line, transaction, trigger):
        ''' TransactionTraceCollectTime helper function '''
        groups = []
        match = re.match(trigger.msg_timestamp_trigger, input_line)
        if match:
            groups = match.groups()
            assert(len(groups) == 3)
            message_id = groups[0]
            transaction.set_field(message_id, 'message_id', message_id)
            transaction.set_field(message_id, 'timestamp', groups[1])
            transaction.set_field(message_id, 'type', groups[2]) 
        return groups
        

    def empty_line(self):
        ''' All timestamps collected. Capture individual messages'''
        self.context.state_start_message.initialize_state()
        self.context.set_state(self.context.state_start_message)
    
    
class TransactionTraceStartMessage(TransactionTraceState):
    ''' State: Find beginning of message'''

    def __init__(self, context):
        super().__init__(context)
        self.initialize_state()

    def initialize_state(self):
        self.context.empty_lines = 0
    
    def process_line(self, input_line):
        transaction = self.context.current_transaction
        trigger = transaction.get_trigger()
        match = re.match(trigger.msg_trigger, input_line)
        if match:
            self.context.current_message_id = match.group(1)
            self.context.set_state(self.context.state_collect_section)
            return
        self.initialize_state()

    def empty_line(self):
        ''' All timestamps collected. Capture individual messages'''
        if self.context.empty_lines:
            # Empty line already found. all messages captured
            self.context.update_result()
            self.context.empty_lines = 0
            self.context.set_state(self.context.state_search_for_start)    
        else:
            # First empty line found. Keep searching for messages
            self.context.empty_lines += 1

        
class TransactionTraceCollectSection(TransactionTraceState):
    ''' State: Collecting sections within a message '''
    
    def __init__(self, context):
        super().__init__(context)
    
    def process_line(self, input_line):
        transaction = self.context.current_transaction
        trigger = transaction.get_trigger()
        message_id = self.context.current_message_id     
        # Checks first for beginning of section
        if self.check_section_triggers(input_line, transaction, trigger, message_id):
            return True
        # New section not found. Check for section parameters
        self.check_section_parms(input_line, transaction, trigger, message_id)
        return True
    
    def check_section_triggers(self, input_line, transaction, trigger, message_id):
        for sect_trigger in trigger.section_triggers:
            match = re.search(sect_trigger.section_trigger, input_line)
            if match:
                self.context.current_section_trigger = sect_trigger
                return True
    
    def check_section_parms(self, input_line, transaction, trigger, message_id):
        current_section_trigger = self.context.current_section_trigger
        if current_section_trigger:
            for parameter in current_section_trigger.parameters:
                match = re.search(parameter, input_line)
                if match:
                    _, value = self.get_key_value(input_line)
                    formatted_name = self.format_section_parm_name(parameter)
                    transaction.set_field(message_id,
                                          formatted_name,
                                          value)
    
    def format_section_parm_name(self, parameter):
        current_section_trigger = self.context.current_section_trigger
        section_parm_name = current_section_trigger.section_trigger.strip()
        section_parm_name += ' - '
        section_parm_name += parameter.replace('=', '')
        section_parm_name = section_parm_name.replace('\\n', '')
        section_parm_name = section_parm_name.replace('\\r', '')
        return section_parm_name.strip()
        
    def get_key_value(self, input_line, sep='='):
        ''' Helper function to extract key : value pairs '''
        key, value = None, None
        input_line = input_line.split(sep)
        if len(input_line) >= 2:
            key, value = [x.strip() for x in input_line][:2]
        return key, value        

    def empty_line(self):
        ''' All parameters collected. Next message'''
        self.context.set_state(self.context.state_start_message)    
    
    def initialize_state(self):
        self.context.empty_lines = 0
