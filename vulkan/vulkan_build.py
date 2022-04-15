from cffi import FFI
import os

HERE = os.path.dirname(os.path.realpath(__file__))

ffi = FFI()

if "nt" == os.name:
    infile = os.path.join(HERE, 'vulkan.cdef_windows.h')
else:
    infile = os.path.join(HERE, 'vulkan.cdef.h')


# read file
with open(infile) as f:
    cdef = f.read()

# configure cffi
# cdef() expects a single string declaring the C types, functions and
# globals needed to use the shared object. It must be in valid C syntax.
ffi.cdef(cdef)

# set_source() gives the name of the python extension module to
# produce, and some C source code as a string.  This C code needs
# to make the declarated functions, types and globals available,
# so it is often just the "#include".
ffi.set_source('vulkan._vulkancache', None)
