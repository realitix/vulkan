from itertools import zip_longest
from os import path
import subprocess

import inflection
import jinja2
import xmltodict


HERE = path.dirname(path.abspath(__file__))
VENDOR_EXTENSIONS = ['KHR', 'EXT', 'NV']

CUSTOM_FUNCTIONS = ('vkGetInstanceProcAddr', 'vkGetDeviceProcAddr',
                    'vkMapMemory', 'vkGetPipelineCacheData')
NULL_MEMBERS = ('pNext', 'pAllocator', 'pUserData')


def get_enum_names(vk):
    return {e['@name'] for e in vk['registry']['enums']}


def get_handle_names(vk):
    return {s['name'] for s in vk['registry']['types']['type']
            if s.get('@category', None) == 'handle'}


def get_struct_names(vk):
    return {s['@name'] for s in vk['registry']['types']['type']
            if s.get('@category', None) == 'struct'}


def get_union_names(vk):
    return {s['name'] for s in vk['registry']['types']['type']
            if s.get('@category', None) == 'union'}


def parse_constant(constant, ext_number=0):
    if '@bitpos' in constant:
        value = constant['@bitpos']
        num_val = int(value, 0)
        num_val = 1 << num_val
        return '0x%08x' % num_val
    elif '@value' in constant:
        return constant['@value']
    elif '@offset' in constant:
        ext_base = 1000000000
        ext_block_size = 1000
        value = ext_base + (ext_number - 1) * ext_block_size
        value += int(constant['@offset'])
        if constant.get('@dir') == '-':
            value = -value

        return value


def model_typedefs(vk, model):
    """Fill the model with typedefs

    model['typedefs'] = {'name': 'type', ...}
    """
    model['typedefs'] = {}

    # bitmasks and basetypes
    bitmasks = [x for x in vk['registry']['types']['type']
                if x.get('@category') == 'bitmask']

    basetypes = [x for x in vk['registry']['types']['type']
                 if x.get('@category') == 'basetype']

    for typedef in bitmasks + basetypes:
        model['typedefs'][typedef['name']] = typedef['type']

    # handles
    handles = [x for x in vk['registry']['types']['type']
               if x.get('@category') == 'handle']

    for handle in handles:
        n = handle['name']
        t = handle['type']
        if t == 'VK_DEFINE_HANDLE':
            model['typedefs']['struct %s_T' % n] = '*%s' % n
        if t == 'VK_DEFINE_HANDLE':
            model['typedefs'][n] = 'uint64_t'

    # custom plaform dependant
    for name in ['Display', 'xcb_connection_t', 'wl_display', 'wl_surface',
                 'MirConnection', 'MirSurface', 'ANativeWindow',
                 'SECURITY_ATTRIBUTES']:
        model['typedefs'][name] = 'struct %s' % name

    model['typedefs'].update({
        'Window': 'uint32_t', 'VisualID': 'uint32_t',
        'xcb_window_t': 'uint32_t', 'xcb_visualid_t': 'uint32_t'
    })


def model_enums(vk, model):
    """Fill the model with enums

    model['enums'] = {'name': {'item_name': 'item_value'...}, ...}
    """
    model['enums'] = {}

    # init enums dict
    enums_type = [x['@name'] for x in vk['registry']['types']['type']
                  if x.get('@category') == 'enum']

    for name in enums_type:
        model['enums'][name] = {}

    # create enums
    enums = [x for x in vk['registry']['enums']
             if x.get('@type') in ('enum', 'bitmask')]

    for enum in enums:
        name = enum['@name']
        t = enum.get('@type')

        # enum may have no enums (because of extension)
        if not enum.get('enum'):
            continue

        if t in ('enum', 'bitmask'):
            # add attr to enum
            for attr in enum['enum']:
                if '@bitpos' in attr:
                    num_val = int(attr['@bitpos'], 0)
                    num_val = 1 << num_val
                    val = '0x%08x' % num_val
                elif '@value' in attr:
                    val = attr['@value']

                model['enums'][name][attr['@name']] = val

        # Add computed value
        def ext_name(name, extension):
            if extension:
                return name + '_' + extension
            return name

        extension = next(iter([x for x in VENDOR_EXTENSIONS
                               if name.lower().endswith(x)]), '').upper()

        standard_name = inflection.underscore(name).upper()
        if extension:
            standard_name = standard_name.split(extension)[0][:-1]

        if t == 'bitmask':
            en = ext_name(standard_name, '_MAX_ENUM')
            model['enums'][name][en] = 0x7FFFFFFF
        else:
            values = [int(x) for x in model['enums'][name].values()]

            begin_attr = ext_name(standard_name, '_BEGIN_RANGE')
            end_attr = ext_name(standard_name, '_END_RANGE')
            size_attr = ext_name(standard_name, '_RANGE_SIZE')
            max_attr = ext_name(standard_name, '_MAX_ENUM')

            model['enums'][name][begin_attr] = min(values)
            model['enums'][name][end_attr] = max(values)
            model['enums'][name][size_attr] = max(values) - min(values) + 1
            model['enums'][name][max_attr] = 0x7FFFFFFF


def model_macros(vk, model):
    """Fill the model with macros

    model['macros'] = {'name': value, ...}
    """
    model['macros'] = {}

    # API Macros
    macros = [x for x in vk['registry']['enums']
              if x.get('@type') not in ('bitmask', 'enum')]

    special_values = {'1000.0f': '1000.0', '(~0U)': 0xffffffff, '(~0ULL)': -1}

    for macro in macros[0]['enum']:
        name = macro['@name']
        value = macro['@value']

        if value in special_values:
            value = special_values[value]

        model['macros'][name] = value

    # Extension Macros
    extensions = [x for x in vk['registry']['extensions']['extension']]

    for ext in extensions:
        model['macros'][ext['@name']] = 1
        for req in ext['require']:
            for enum in req['enum']:
                ename = enum['@name']
                evalue = parse_constant(enum, int(ext['@number']))

                if enum.get('@extends') == 'VkResult':
                    model['enums']['VkResult'][ename] = evalue
                else:
                    model['macros'][ename] = evalue


def model_funcpointers(vk, model):
    """Fill the model with function pointer

    model['funcpointers'] = {'pfn_name': 'struct_name'}
    """
    model['funcpointers'] = {}

    funcs = [x for x in vk['registry']['types']['type']
             if x.get('@category') == 'funcpointer']
    structs = [x for x in vk['registry']['types']['type']
               if x.get('@category') == 'struct']

    for f in funcs:
        pfn_name = f['name']
        for s in structs:
            for m in s['member']:
                if m['type'] == pfn_name:
                    struct_name = s['@name']
        model['funcpointers'][pfn_name] = struct_name


def model_exceptions(vk, model):
    """Fill the model with exceptions and errors

    model['exceptions'] = {val: 'name',...}
    model['errors'] = {val: 'name',...}
    """
    model['exceptions'] = {}
    model['errors'] = {}

    all_codes = model['enums']['VkResult']
    success_names = set()
    error_names = set()

    commands = [x for x in vk['registry']['commands']['command']]

    for command in commands:
        successes = command.get('@successcodes', '').split(',')
        errors = command.get('@errorcodes', '').split(',')
        success_names.update(successes)
        error_names.update(errors)

    for key, value in all_codes.items():
        if key.startswith('VK_RESULT') or key == 'VK_SUCCESS':
            continue
        name = inflection.camelize(key.lower())

        if key in success_names:
            model['exceptions'][value] = name
        elif key in error_names:
            model['errors'][value] = name
        else:
            print('Warning: return code %s unused' % key)


def model_constructors(vk, model):
    """Fill the model with constructors

    model['constructors'] = [{'name': 'x', 'members': [{'name': 'y'}].}]
    """
    model['constructors'] = []
    structs = [x for x in vk['registry']['types']['type']
               if x.get('@category') in {'struct', 'union'}]

    def parse_len(member):
        mlen = member.get('@len')
        if not mlen:
            return None

        if ',' in mlen:
            mlen = mlen.split(',')[0]

        if 'latex' in mlen or 'null-terminated' in mlen:
            return None

        return mlen

    for struct in structs:
        model['constructors'].append({
            'name': struct['@name'],
            'members': [{
                'name': x['name'],
                'type': x['type'],
                'default': x.get('@values'),
                'len': parse_len(x)
            } for x in struct['member']]
        })


def model_functions(vk, model):
    """Fill the model with functions"""

    def get_vk_extension_functions():
        names = set()
        for extension in vk['registry']['extensions']['extension']:
            for req in extension['require']:
                if 'command' not in req:
                    continue
                for command in req['command']:
                    names.add(command['@name'])
        return names

    def get_count_param(command):
        for param in command['param']:
            if param['type'] + param.get('#text', '') == 'uint32_t*':
                return param
        return None

    def member_has_str(name):
        c = next(iter([x for x in model['constructors']
                       if x['name'] == name]), None)
        if c and any(['char' in x['type'] for x in c['members']]):
            return True
        return False

    def format_member(member):
        type_name = member['type']
        if '#text' in member:
            text = member['#text'].replace('const ', '').strip()
            type_name += ' ' + text

        return {'name': member['name'],
                'type': member['type'],
                'none': member['name'] in NULL_MEMBERS,
                'force_array': True if '@len' in member else False,
                'to_create': False,
                'has_str': member_has_str(member['type'])}

    def format_return_member(member):
        t = member['type']

        static_count = None
        if '@len' in member and '::' in member['@len']:
            lens = member['@len'].split('::')
            static_count = {'key': lens[0], 'value': lens[1]}

        is_handle = t in get_handle_names(vk)
        is_enum = t in get_enum_names(vk)
        is_struct = t in get_struct_names(vk)
        return {'name': member['name'],
                'type': t,
                'handle': is_handle,
                'enum': is_enum,
                'struct': is_struct,
                'static_count': static_count,
                'has_str': member_has_str(member['type'])}

    ALLOCATE_PREFIX = ('vkCreate', 'vkGet', 'vkEnumerate', 'vkAllocate',
                       'vkMap', 'vkAcquire')
    ALLOCATE_EXCEPTION = ('vkGetFenceStatus', 'vkGetEventStatus',
                          'vkGetQueryPoolResults',
                          'vkGetPhysicalDeviceXlibPresentationSupportKHR')
    COUNT_EXCEPTION = ('vkAcquireNextImageKHR',)

    model['functions'] = []
    model['extension_functions'] = []
    functions = [f for f in vk['registry']['commands']['command']]
    extension_function_names = get_vk_extension_functions()

    for function in functions:
        fname = function['proto']['name']
        ftype = function['proto']['type']

        if fname in CUSTOM_FUNCTIONS:
            continue

        if type(function['param']) is not list:
            function['param'] = [function['param']]

        count_param = get_count_param(function)
        if fname in COUNT_EXCEPTION:
            count_param = None
        is_allocate = any([fname.startswith(a) for a in ALLOCATE_PREFIX])
        is_count = is_allocate and count_param is not None

        if fname in ALLOCATE_EXCEPTION or ftype == 'VkBool32':
            is_allocate = is_count = False

        members = []
        for member in function['param']:
            members.append(format_member(member))

        return_member = None
        if is_allocate:
            return_member = format_return_member(function['param'][-1])
            members[-1]['to_create'] = True
        if is_count:
            members[-2]['to_create'] = True

        f = {
            'name': fname,
            'members': members,
            'allocate': is_allocate,
            'count': is_count,
            'return_boolean': True if ftype == 'VkBool32' else False,
            'return_result': True if ftype == 'VkResult' else False,
            'return_member': return_member,
            'is_extension': fname in extension_function_names
        }

        model['functions'].append(f)


def model_ext_functions(vk, model):
    """Fill the model with extensions functions"""
    model['ext_functions'] = {'instance': set(), 'device': set()}

    extensions = [x for x in vk['registry']['extensions']['extension']]

    for extension in extensions:
        for req in extension['require']:
            if not req.get('command'):
                continue

            command_names = [x['@name'] for x in req['command']]
            ext_type = extension['@type']
            model['ext_functions'][ext_type].update(command_names)


def init():
    with open(path.join(HERE, 'vk.xml')) as f:
        xml = f.read()

    return xmltodict.parse(xml, force_list=('enum', 'command', 'member'))


def format_vk(vk):
    """Format vk before using it"""

    # Force extension require to be a list
    extensions = [x for x in vk['registry']['extensions']['extension']]
    for ext in extensions:
        if not isinstance(ext['require'], list):
            ext['require'] = [ext['require']]


def generate_py():
    """Generate the python output file"""
    model = {}

    vk = init()
    format_vk(vk)
    model_typedefs(vk, model)
    model_enums(vk, model)
    model_macros(vk, model)
    model_funcpointers(vk, model)
    model_exceptions(vk, model)
    model_constructors(vk, model)
    model_functions(vk, model)
    model_ext_functions(vk, model)

    env = jinja2.Environment(
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        loader=jinja2.FileSystemLoader(HERE)
    )

    out_file = path.join(HERE, path.pardir, 'vulkan', '__init__.py')
    with open(out_file, 'w') as out:
        out.write(env.get_template('vulkan.template.py').render(model=model))


def generate_cdef():
    """Generate the cdef output file"""
    include_path = path.join(HERE, 'fake_libc_include')
    out_file = path.join(HERE, path.pardir, '_cffi_build', 'vulkan.cdef.h')
    header = path.join(HERE, 'vulkan.h')

    command = ['cpp',
               '-std=c99',
               '-P',
               '-nostdinc',
               '-I' + include_path,
               '-o' + out_file,
               '-DVK_USE_PLATFORM_XCB_KHR',
               '-DVK_USE_PLATFORM_WAYLAND_KHR',
               '-DVK_USE_PLATFORM_ANDROID_KHR',
               '-DVK_USE_PLATFORM_WIN32_KHR',
               '-DVK_USE_PLATFORM_XLIB_KHR',
               header]
    subprocess.run(command, check=True)


def main():
    """Main function to generate files"""
    generate_cdef()
    generate_py()


if __name__ == '__main__':
    main()
