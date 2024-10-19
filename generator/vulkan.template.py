from collections.abc import Iterable
import weakref as _weakref
import sys

from vulkan._vulkancache import ffi


_weakkey_dict = _weakref.WeakKeyDictionary()
PY3 = sys.version_info >= (3, 0)


class ProcedureNotFoundError(Exception):
    pass


class ExtensionNotSupportedError(Exception):
    pass


def _cstr(x):
    if not isinstance(x, ffi.CData):
        return x

    t = ffi.typeof(x)
    if 'item' not in dir(t) or t.item.cname != 'char':
        return x

    if PY3:
        try:
            return ffi.string(x).decode('ascii')
        except UnicodeDecodeError:
            return ffi.string(x).decode('utf-8')
    else:
        return ffi.string(x)


class StrWrap(object):
    """Wrap a FFI Cdata object

    This class is a proxy class which auto-convert FFI string to Python
    string. It must be used only on object containing string data.
    Original CFFI string can always be accessed by prefixing the property with
    an underscore.
    """
    def __init__(self, obj):
        self.obj = obj

    def __setattr__(self, key, value):
        if key == 'obj':
            return super(StrWrap, self).__setattr__(key, value)

        setattr(self.obj, key, value)

    def __getattr__(self, key):
        try:
            attr = getattr(self.obj, key)
        except AttributeError as origin_exc:
            # Remove the first underscore if exists
            if key.startswith('_'):
                try:
                    return getattr(self.obj, key[1:])
                except AttributeError:
                    raise origin_exc
            raise origin_exc

        return _cstr(attr)


def _cast_ptr2(x, _type):
    if isinstance(x, ffi.CData):
        if (_type.item == ffi.typeof(x) or
            (_type.item.cname == 'void' and ffi.typeof(x).kind in
             ['struct', 'union'])):
            return ffi.addressof(x), x
        return x, x

    if isinstance(x, Iterable):
        if _type.item.kind == 'pointer':
            ptrs = [_cast_ptr(i, _type.item) for i in x]
            ret = ffi.new(_type.item.cname+'[]', [i for i, _ in ptrs])
            _weakkey_dict[ret] = tuple(i for _, i in ptrs if i != ffi.NULL)
        else:
            ret = ffi.new(_type.item.cname+'[]', x)

        if isinstance(x, list):
            iterable_references = []
            for item in x:
                if item in _weakkey_dict:
                    iterable_references.append(_weakkey_dict[item])
            if iterable_references:
                _weakkey_dict[ret] = iterable_references

        return ret, ret

    return ffi.cast(_type, x), x


def _cast_ptr3(x, _type):
    if isinstance(x, str):
        try:
            x = x.encode('ascii')
        except UnicodeEncodeError:
            x = x.encode('utf-8')
    return _cast_ptr2(x, _type)


_cast_ptr = _cast_ptr3 if PY3 else _cast_ptr2


# Load SDK
_lib_names = ('libvulkan.so.1', 'vulkan-1.dll', 'libvulkan.dylib')
for name in _lib_names:
    try:
        lib = ffi.dlopen(name)
        break
    except OSError:
        pass
else:
    raise OSError('Cannot find Vulkan SDK version. Please ensure that it is '
                  'installed and that the <sdk_root>/<version>/lib/ folder is '
                  'in the library path')


{# Add enums #}
{% for _, enums in model.enums.items() %}
{% for name, value in enums.items() %}
{{name}} = {{value}}
{% endfor %}
{% endfor %}

def VK_MAKE_VERSION(major, minor, patch):
    return (((major) << 22) | ((minor) << 12) | (patch))


def VK_VERSION_MAJOR(version):
    return version >> 22


def VK_VERSION_MINOR(version):
    return (version >> 12) & 0x3ff


def VK_VERSION_PATCH(version):
    return version & 0xfff


VK_API_VERSION = VK_MAKE_VERSION(1, 0, 0)
VK_API_VERSION_1_0 = VK_MAKE_VERSION(1, 0, 0)
VK_NULL_HANDLE = 0
_UINT64_MAX = ffi.new('unsigned long long int*', 18446744073709551615)
UINT64_MAX = _UINT64_MAX[0]


{# iterate two times to handle dependacy between constants #}
{% for name, value in model.macros.items() %}
{% if value is not string %}
{{name}} = {{value}}
{% elif value is string and not value.startswith('VK_') %}
{{name}} = {{value}}
{% endif %}
{% endfor %}

{% for name, value in model.macros.items() %}
{% if value is string and value.startswith('VK_') %}
{{name}} = {{value}}
{% endif %}
{% endfor %}



class VkException(Exception):
    pass


class VkError(Exception):
    pass


{% for name in model.exceptions.values() %}
class {{name}}(VkException):
    pass
{% endfor %}

{% for name in model.errors.values() %}
class {{name}}(VkError):
    pass
{% endfor %}

exception_codes = {
{% for value, name in model.exceptions.items() %}
    {{value}}:{{name}},
{% endfor %}

{% for value, name in model.errors.items() %}
    {{value}}:{{name}},
{% endfor %}
}

{% for name in model.funcpointers %}
{% set fname = name[4:] %}
_internal_{{fname}} = None

@ffi.callback('{{name}}')
def _external_{{fname}}(*args):
    return _internal_{{fname}}(*[_cstr(x) for x in args])
{% endfor %}


def _get_pfn_name(struct_name):
{% for k, v in model.funcpointers.items() %}
{% set fname = k[4:] %}
    if struct_name == '{{v}}':
        return '{{fname}}'
{% endfor %}


def _new(ctype, **kwargs):
    _type = ffi.typeof(ctype)

    # keep only valued kwargs
    kwargs = {k: kwargs[k] for k in kwargs if kwargs[k]}

    # cast pointer
    ptrs = {}
    pfns = {}
    pcs = {}
    for k, v in kwargs.items():
        # convert tuple pair to dict
        ktype = dict(_type.fields)[k].type

        if k == 'pCode':
            pcs[k] = ffi.cast('uint32_t*', ffi.from_buffer(v))
        elif k.startswith('pfn'):
            pfn_name = _get_pfn_name(ctype)
            mod = sys.modules[__name__]
            setattr(mod, '_internal_' + pfn_name, v)
            pfns[k] = getattr(mod, '_external_' + pfn_name)
        elif ktype.kind == 'pointer':
            ptrs[k] = _cast_ptr(v, ktype)

    # init object
    init = dict(kwargs,  **{k: v for k, (v, _) in ptrs.items()})
    init.update(pfns)
    init.update(pcs)

    ret = ffi.new(_type.cname + '*', init)[0]

    # reference created pointer in the object
    _weakkey_dict[ret] = [v for _, v in ptrs.values() if v != ffi.NULL]
    if pcs:
        _weakkey_dict[ret].extend([x for x in pcs.values()])

    return ret



{# Macro for function parameters #}
{%- macro constructor_params(c) -%}
    {%- for m in c.members -%}
        {%- if m.default -%}
            {{m.name}}={{m.default}}
        {%- else -%}
            {{m.name}}=None
        {%- endif -%},
    {%- endfor -%}
{%- endmacro -%}

{%- macro constructor_params_call(c) -%}
    {%- for m in c.members -%}
        {{m.name}}={{m.name}}
        {%- if not loop.last -%}
        ,
        {%- endif -%}
    {%- endfor -%}
{%- endmacro -%}

{%- macro constructor_len(c) -%}
{% for m in c.members %}
{% if m.len %}
    if {{m.len}} is None and {{m.name}} is not None:
        {{m.len}} = len({{m.name}})
{% endif %}
{% endfor %}
{%- endmacro -%}


{% for constructor in model.constructors %}
def {{constructor.name}}({{constructor_params(constructor)}}):
{{constructor_len(constructor)}}
    return _new('{{constructor.name}}', {{constructor_params_call(constructor)}})

{% endfor %}


def _auto_handle(x, _type):
    if x is None:
        return ffi.NULL
    if _type.kind == 'pointer':
        ptr, _ = _cast_ptr(x, _type)
        return ptr
    return x


def _callApi(fn, *args):
    fn_args = [_auto_handle(i, j) for i, j in zip(args, ffi.typeof(fn).args)]
    return fn(*fn_args)


{# Macro for function parameters #}
{%- macro params_def(f) -%}
    {% set members = f.members %}
    {% set optional_members = [] %}

    {% if f.count %}
        {% set members = f.members[:-2] %}
    {% elif f.allocate %}
        {% set members = f.members[:-1] %}
        {% set optional_members = [f.members[-1]]%}
    {% endif %}

    {%- for m in members -%}
        {{m.name}}
        ,
    {%- endfor -%}
    {%- for m in optional_members -%}
        {{m.name}}=None
        ,
    {%- endfor -%}
{%- endmacro -%}

{%- macro params_call(f) -%}
    {%- for m in f.members -%}
        {{m.name}}
        {%- if not loop.last -%}
        ,
        {%- endif -%}
    {%- endfor -%}
{%- endmacro -%}


{# Macro that write a function #}
{% macro fun_allocate(f) %}
{% set fn_call = 'lib.' ~ f.name %}
{% if f.is_extension %} {% set fn_call = 'fn' %} {% endif %}
def {{f.name}}({{params_def(f)}}):
    {% set rmember = f.return_member %}

    custom_return = True
    if not {{rmember.name}}:
        {% if rmember.static_count %}
        {% set sc = rmember.static_count %}
        {{rmember.name}} = ffi.new('{{rmember.type}}[%d]' % {{sc}})
        {% else %}
        {{rmember.name}} = ffi.new('{{rmember.type}}*')
        {% endif %}
        custom_return = False

    result = _callApi({{fn_call}}, {{params_call(f)}})
    {% if f.return_result %}
    if result != VK_SUCCESS:
        raise exception_codes[result]
    {% endif %}

    if custom_return:
        return {{rmember.name}}

    {% if not rmember.static_count and not rmember.has_str %}
    return {{rmember.name}}[0]
    {% elif not rmember.static_count and rmember.has_str %}
    return StrWrap({{rmember.name}}[0])
    {% else %}
    return {{rmember.name}}
    {% endif %}

{% endmacro %}

{% macro fun_count(f) %}
{% set fn_call = 'lib.' ~ f.name %}
{% if f.is_extension %} {% set fn_call = 'fn' %} {% endif %}
def {{f.name}}({{params_def(f)}}):
    {% set cmember = f.members[-2] %}
    {% set amember = f.members[-1] %}

    {{cmember.name}} = ffi.new('{{cmember.type}}*')
    {{amember.name}} = ffi.NULL

    result = _callApi({{fn_call}}, {{params_call(f)}})
    {% if f.return_result %}
    if result != VK_SUCCESS:
        raise exception_codes[result]
    {% endif %}

    {{amember.name}} = ffi.new('{{amember.type}}[]', {{cmember.name}}[0])
    result = _callApi({{fn_call}}, {{params_call(f)}})
    {% if f.return_result %}
    if result != VK_SUCCESS:
        raise exception_codes[result]
    {% endif %}

    {% if amember.has_str %}
    result = (StrWrap(x) for x in {{amember.name}})
    _weakkey_dict[result] = {{amember.name}}
    return result
    {% else %}
    return {{amember.name}}
    {% endif %}
{% endmacro %}

{% macro fun_noallocate(f) %}
{% set fn_call = 'lib.' ~ f.name %}
{% if f.is_extension %} {% set fn_call = 'fn' %} {% endif %}
def {{f.name}}({{params_def(f)}}):
    result = _callApi({{fn_call}}, {{params_call(f)}})
    {% if f.return_result %}
    if result != VK_SUCCESS:
        raise exception_codes[result]
    {% endif %}
{% endmacro %}

{% macro fun(f) %}
{% if f.count %}
{{fun_count(f)}}
{% elif f.allocate %}
{{fun_allocate(f)}}
{% else %}
{{fun_noallocate(f)}}
{% endif %}
{% endmacro %}


{# Write functions and extensions functions #}
{% for f in model.functions %}
{% if f.is_extension %}
def _wrap_{{f.name}}(fn):
  {{fun(f)|indent()}}
    return {{f.name}}
{% else %}
{{fun(f)}}
{% endif %}
{% endfor %}

_instance_ext_funcs = {
{% for k, v in model.ext_functions.instance.items() %}
    '{{k}}':_wrap_{{v}},
{% endfor %}
{# device functions can be accessed with getInstance.. but it's not the best way #}
{% for k, v in model.ext_functions.device.items() %}
    '{{k}}':_wrap_{{v}},
{% endfor %}
}


_device_ext_funcs = {
{% for k, v in model.ext_functions.device.items() %}
    '{{k}}':_wrap_{{v}},
{% endfor %}
}


def vkGetInstanceProcAddr(instance, pName):
    fn = _callApi(lib.vkGetInstanceProcAddr, instance, pName)
    if fn == ffi.NULL:
        raise ProcedureNotFoundError()
    if not pName in _instance_ext_funcs:
        raise ExtensionNotSupportedError()
    fn = ffi.cast('PFN_' + pName, fn)
    return _instance_ext_funcs[pName](fn)


def vkGetDeviceProcAddr(device, pName):
    fn = _callApi(lib.vkGetDeviceProcAddr, device, pName)
    if fn == ffi.NULL:
        raise ProcedureNotFoundError()
    if not pName in _device_ext_funcs:
        raise ExtensionNotSupportedError()
    fn = ffi.cast('PFN_'+pName, fn)
    return _device_ext_funcs[pName](fn)


def vkMapMemory(device, memory, offset, size, flags):
    ppData = ffi.new('void**')

    result = _callApi(lib.vkMapMemory, device,memory,offset,size,flags,ppData)
    if result != VK_SUCCESS:
        raise exception_codes[result]

    return ffi.buffer(ppData[0], size)


{# Alias #}
{% for name, alias in model.alias.items() %}
#{{name}} = {{alias}}
{% endfor %}
