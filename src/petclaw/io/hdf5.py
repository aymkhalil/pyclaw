#!/usr/bin/env python
# encoding: utf-8
r"""
Routines for reading and writing a HDF5 output file

This module reads and writes hdf5 files via either of the following modules:
    h5py - http://code.google.com/p/h5py/
    PyTables - http://www.pytables.org/moin

It will first try h5py and then PyTables and use the correct calls
according to whichever is present on the system.  We recommend that you use
h5py as it is a minimal wrapper to the HDF5 library.

To install either, you must also install the hdf5 library from the website:
    http://www.hdfgroup.org/HDF5/release/obtain5.html
"""

from mpi4py import MPI
import os
import logging

from clawpack import pyclaw
from clawpack.pyclaw.io.hdf5 import read

logger = logging.getLogger('pyclaw.io')

# Import appropriate hdf5 package
use_h5py = False
use_PyTables = False
try:
    import h5py
    use_h5py = True
except:
    try:
        import tables
        use_PyTables = True
    except:
        logging.critical("Could not import h5py or PyTables!")
        error_msg = ("Could not import h5py or PyTables, please install " +
            "either h5py or PyTables.  See the doc_string for more " +
            "information.")
        raise Exception(error_msg)

def write(solution,frame,path,file_prefix='claw',write_aux=False,
                options={},write_p=False):

    r"""
    Write out a Solution to a HDF5 file.
    
    :Input:
     - *solution* - (:class:`~pyclaw.solution.Solution`) Pyclaw solution 
       object to input into
     - *frame* - (int) Frame number
     - *path* - (string) Root path
     - *file_prefix* - (string) Prefix for the file name.  ``default = 'claw'``
     - *write_aux* - (bool) Boolean controlling whether the associated 
       auxiliary array should be written out.  ``default = False``     
     - *options* - (dict) Optional argument dictionary, see 
       `HDF5 Option Table`_
    
    .. _`HDF5 Option Table`:
    
    +-----------------+------------------------------------------------------+
    | Key             | Value                                                |
    +=================+======================================================+
    | compression     | (None, string ["gzip" | "lzf" | "szip"] or int 0-9)  |
    |                 | Enable dataset compression. DEFLATE, LZF and (where  |
    |                 | available) SZIP are supported. An integer is         |
    |                 | interpreted as a GZIP level for backwards            |
    |                 | compatibility.                                       |
    +-----------------+------------------------------------------------------+
    |compression_opts | (None, or special value) Setting for compression     |
    |                 | filter; legal values for each filter type are:       |
    |                 |                                                      |
    |                 | - *gzip* - (int) 0-9                                 |
    |                 | - *lzf* - None allowed                               |
    |                 | - *szip* - (tuple) 2-tuple ('ec'|'nn', even integer  |
    |                 |     0-32)                                            |
    |                 |                                                      |
    |                 | See the filters module for a detailed description of |
    |                 | each of these filters.                               |
    +-----------------+------------------------------------------------------+
    | chunks          | (None, True or shape tuple) Store the dataset in     |
    |                 | chunked format. Automatically selected if any of the |
    |                 | other keyword options are given. If you don't provide|
    |                 | a shape tuple, the library will guess one for you.   |
    +-----------------+------------------------------------------------------+
    | shuffle         | (True/False) Enable/disable data shuffling, which can|
    |                 | improve compression performance. Automatically       |
    |                 | enabled when compression is used.                    |
    +-----------------+------------------------------------------------------+
    | fletcher32      | (True/False) Enable Fletcher32 error detection; may  |
    |                 | be used with or without compression.                 |
    +-----------------+------------------------------------------------------+
    """
    option_defaults = {'compression':None,'compression_opts':None,
                       'chunks':None,'shuffle':False,'fletcher32':False}
    for (k,v) in option_defaults.iteritems():
        options[k] = options.get(k,v)
    
    filename = os.path.join(path,'%s%s.hdf' % 
                                (file_prefix,str(frame).zfill(4)))

    if options['compression'] is not None:
        err_msg = "Compression (filters) are not available for parallel h5py yet."
        logging.critical(err_msg)
        raise Exception(err_msg)
    
    if use_h5py:
        with h5py.File(filename,'w',driver='mpio',comm=MPI.COMM_WORLD) as f:
        
            # For each patch, write out attributes
            for state in solution.states:
                patch = state.patch
                # Create group for this patch
                subgroup = f.create_group('patch%s' % patch.patch_index)

                # General patch properties
                subgroup.attrs['t'] = state.t
                subgroup.attrs['num_eqn'] = state.num_eqn
                subgroup.attrs['num_aux'] = state.num_aux
                for attr in ['num_ghost','patch_index','level']:
                    if hasattr(patch,attr):
                        if getattr(patch,attr) is not None:
                            subgroup.attrs[attr] = getattr(patch,attr)

                # Add the dimension names as a attribute
                subgroup.attrs['dimensions'] = patch.get_dim_attribute('name')
                # Dimension properties
                for dim in patch.dimensions:
                    for attr in ['num_cells','lower','delta','upper',
                                 'units']:
                        if hasattr(dim,attr):
                            if getattr(dim,attr) is not None:
                                attr_name = '%s.%s' % (dim.name,attr)
                                subgroup.attrs[attr_name] = getattr(dim,attr)

                if write_p:
                    q = state.p
                else:
                    q = state.q
                r = patch._da.getRanges()
                globalSize = []
                globalSize.append(q.shape[0])
                globalSize.extend(patch.num_cells_global)
                dset = subgroup.create_dataset('q',globalSize,dtype='float',**options)
                if len(patch.name) == 1:
                    dset[:,r[0][0]:r[0][1]] = q
                elif len(patch.name) == 2:
                    dset[:,r[0][0]:r[0][1],r[1][0]:r[1][1]] = q
                elif len(patch.name) == 3:
                    dset[:,r[0][0]:r[0][1],r[1][0]:r[1][1],r[2][0]:r[2][1]] = q

                if write_aux and state.num_aux > 0:
                    r = patch._da.getRanges()
                    globalSize = []
                    globalSize.append(state.num_aux)
                    globalSize.extend(patch.num_cells_global)
                    dset = subgroup.create_dataset('aux',globalSize,dtype='float',**options)
                    if len(patch.name) == 1:
                        dset[:,r[0][0]:r[0][1]] = state.aux
                    elif len(patch.name) == 2:
                        dset[:,r[0][0]:r[0][1],r[1][0]:r[1][1]] = state.aux
                    elif len(patch.name) == 3:
                        dset[:,r[0][0]:r[0][1],r[1][0]:r[1][1],r[2][0]:r[2][1]] = state.aux
        
    elif use_PyTables:
        # f = tables.openFile(filename, mode = "w", title = options['title'])
        logging.critical("PyTables has not been implemented yet.")
        raise IOError("PyTables has not been implemented yet.")
    else:
        err_msg = "No hdf5 python modules available."
        logging.critical(err_msg)
        raise Exception(err_msg)

