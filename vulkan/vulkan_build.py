from cffi import FFI
from os import path

HERE = path.dirname(path.realpath(__file__))

ffi = FFI()

# read file
with open(path.join(HERE, 'vulkan.cdef.h')) as f:
    cdef = f.read()

# configure cffi
ffi.cdef(cdef)
ffi.set_source('vulkan._vulkancache', None)
