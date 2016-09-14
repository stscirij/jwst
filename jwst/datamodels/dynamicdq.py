from __future__ import print_function
import numpy as np
from . import dqflags

def dynamic_mask(input_model):
    #
    # Return a mask model given a mask with dynamic DQ flags
    # Dynamic flags define what each plane refers to using the DQ_DEF extension

    dq_table = input_model.dq_def
    print(type(dq_table))
    print(dq_table.columns)
    # Get the DQ array and the flag definitions
    if (dq_table is not None and
        not np.isscalar(dq_table) and
        len(dq_table.shape) and
        len(dq_table)):
        columnnames = dq_table.names
        print(columnnames)
        # In case the reference file has column names not capitalized
        tblvalue = ColumnThatMatches('VALUE', columnnames)
        print(type(tblvalue), tblvalue)
        tblname = ColumnThatMatches('NAME', columnnames)
        print(type(tblname), tblname)
        #
        # Make an empty mask
        dqmask = np.zeros(input_model.dq.shape, dtype=input_model.dq.dtype)
        for record in dq_table:
            print(type(record))
            print(record['VALUE'])
            print(str(record))
            bitplane = record[tblvalue]
            dqname = record[tblname].strip().upper()
            try:
                standard_bitvalue = dqflags.pixel[dqname]
            except KeyError:
                print('Keyword %s does not correspond to an existing DQ mnemonic, so will be ignored' % (dqname))
                continue
            just_this_bit = np.bitwise_and(input_model.dq, bitplane)
            pixels = np.where(just_this_bit != 0)
            dqmask[pixels] = np.bitwise_or(dqmask[pixels], standard_bitvalue)
    else:
        dqmask = input_model.dq

    return dqmask

def ColumnThatMatches(input_string, list_of_names):
    """
    Find the string in the list that matches the input_string
    Caseless comparison
    """

    for name in list_of_names:
        if caseless_equal(name, input_string):
            return name
    return None

def caseless_equal(left, right):
    return left.lower() == right.lower()
