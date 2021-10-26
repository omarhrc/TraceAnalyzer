# -*- coding: utf-8 -*-
"""
Created on Fri Oct 22 01:17:23 2021

@author: orubio
"""

from trace_analyzer import TraceReaderPlain

TRACE_READER_PLAIN_CONFIG_FILE = 'TraceReaderPlain - config file.txt'
#INPUT_TRACE = 'TraceReaderPlain - Test trace.txt'
INPUT_TRACE = 'VF - GTP - Create PDP_Session - 081021.txt'
OUTPUT_FILE = 'TraceReaderOut.xlsx'


def main():
    reader = TraceReaderPlain(config_filename=TRACE_READER_PLAIN_CONFIG_FILE,
                              trace_filename=INPUT_TRACE)
    df = reader.get_data()
    df.to_excel(OUTPUT_FILE, index=False)
    
if __name__ == "__main__":
    main()

    