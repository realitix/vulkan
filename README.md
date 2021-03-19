<p align="center">
<img src="https://cdn.rawgit.com/realitix/vulkan/182062bc/logo/cvulkan-180x180.png" />
</p>


> *vulkan*, the ultimate Python binding for Vulkan API


# Table of Contents

  * [Presentation](#presentation)
  * [How to install](#how-to-install)
     * [Pip](#pip)
     * [Manual install](#manual-install)
  * [How to use](#how-to-use)
     * [Getting started](#getting-started)
     * [API](#api)
     * [Code convention](#code-convention)
        * [Structs](#structs)
        * [Functions](#functions)
        * [Exceptions](#exceptions)
        * [Constants](#constants)
     * [Resources](#resources)
  * [How to contribute](#how-to-contribute)
  * [Architecture](#architecture)
  * [Community](#community)
  * [Stay in touch](#stay-in-touch)
  * [History](#history)
  * [Supported By](#supported-by)

## Presentation

*vulkan* is a Python extension which supports the Vulkan API. It leverages power of Vulkan with simplicity of Python.
It's a complete Vulkan wrapper, it keeps the original Vulkan API and try to limit differences induced by Python.

*vulkan* is compatible with Python 2 and Python 3.

## How to install

### Pip

You can install directly *vulkan* with pip:

```
pip install vulkan
```

### Manual install

You can install it manually if you want the latest version:

```
git clone https://github.com/realitix/vulkan
cd vulkan
python setup.py install
```


## How to use

### Getting started

To try this wrapper, execute the following commands (on linux):

```bash
git clone https://github.com/realitix/vulkan.git
cd vulkan
python setup.py install
pip install pysdl2
python example/example_sdl2.py
```

Known errors :

`OSError: cannot load library 'libvulkan.so'` means you didn't install the [Vulkan SDK](https://vulkan.lunarg.com/).

`vulkan.VkErrorExtensionNotPresent` means your have installed the Vulkan SDK but your driver doesn't support it.

`pip install vulkan` fails on Windows 10: Try `pip install --upgrade pip setuptools wheel` before installing `vulkan`.


### API

The *vulkan* wrapper gives you complete access to the Vulkan API, including extension functions.


### Code convention

Similar to Vulkan, structs are prefixed with Vk, enumeration values are prefixed with VK_
and functions are prefixed with vk.


#### Structs

Vulkan struct creation is achieved in *vulkan* wrapper using python functions.
For example, if you want to create the Vulkan struct `VkInstanceCreateInfo`,
you must initialize it with its keyword parameters. In *vulkan* wrapper, you will call
the Python function `VkInstanceCreateInfo` with named parameters as shown below.

In **C++** (Vulkan) we write:

```C
VkInstanceCreateInfo instance_create_info = {
    VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO, // sType
    nullptr, // pNext
    0, // flags
    &application_info, // *pApplicationInfo
    3, // enabledLayerCount
    &layers, // *ppEnabledLayerNames
    3, // enabledExtensionCount
    &extensions // *ppEnabledExtensionNames
};
```

Our *vulkan* wrapper equivalent of the above **C++** code is :

```python
import vulkan as vk

instance_create_info = vk.VkInstanceCreateInfo(
    sType=vk.VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
    pNext=None,
    flags=0,
    pApplicationInfo=application_info,
    enabledLayerCount=len(layers),
    ppEnabledLayerNames=layers,
    enabledExtensionCount=len(extensions),
    ppEnabledExtensionNames=extensions,
)
```

To create the struct, you must remember to pass all parameters at creation time.
This includes the Vulkan layers and extensions denoted by `ppEnabledLayerNames`
and `ppEnabledExtensionNames`, which *vulkan* wrapper is able to facilitate too.

This struct example demonstrates how *vulkan* wrapper conveniently converts your
Python code into native C types.

*Note:*

- The default value for all parameters is `None` so you could have omitted `pNext` (because its value is `None`).
- The default value for `sType` parameter is the good value so you could have omitted `sType`.
- The default value for `enabledLayerCount` parameter is the length of `ppEnabledLayerNames` so you could have omitted `enabledLayerCount` and `enabledExtensionCount`.
- Order of parameters doesn't matter since they are keyword parameters.
- The **C++** syntax is more risky because you must pass all parameters in specific order.

#### Functions

*vulkan* greatly simplifies the calling of functions. In Vulkan API, you have to explicitly
write three kinds of function:

  - functions that create nothing
  - functions that create one object
  - functions that create several objects

In *vulkan* wrapper, all these troubles goes away.
*vulkan* will takes care of you and knows when to return `None`, an object or a `list`.
Here are three examples:

```python
# Create one object
instance = vk.vkCreateInstance(createInfo, None)

# Create a list of object
extensions = vk.vkEnumerateDeviceExtensionProperties(physical_device, None)

# Return None
vk.vkQueuePresentKHR(presentation_queue, present_create)
```

Vulkan functions usually return a `VkResult`, which returns the success and
error codes/states of the function. *vulkan* is pythonic and converts `VkResult`
to exception: if the result is not `VK_SUCCESS`, an exception is raised.
More elaboration is given in the next section.


#### Exceptions

- *vulkan* has two types of Exceptions, namely `VkError` or `VkException`.
The `VkError` exception handles all the error codes reported by Vulkan's `VkResult`.
The `VkException` exception handles all the success code reported by Vulkan's `VkResult`,
except the `VK_SUCCESS` success code.

- Exception names are *pythonized*: `VK_NOT_READY` -> `VkNotReady`.

#### Constants

All Vulkan constants are available in *vulkan* and it even provides some fancy
constants like `UINT64_MAX`.


### Resources

To understand how to use this wrapper, you have to look for `example/exemple_*` files
or refer to [Vulk](https://github.com/realitix/vulk) engine.


## How to contribute

To contribute, you should first read the `Architecture` section.
Any contribution is welcome and I answer quickly.


## Architecture

*vulkan* is a CFFI module generated by a Python script.

When you install this module, you need two files:

- `vulkan/vulkan.cdef.h` containing CFFI definitions
- `vulkan/_vulkan.py` containing the actual executed Python script

Theses two files are generated by the `generator/generate.py` script.

`vulkan/vulkan.cdef.h` is generated with a `cpp` command call, it applies pre-processing to the Vulkan C header.
It can't work as is because of `pycparser` which cannot parse the output. That's the purpose of `fake_libc_include` folder.

`vulkan/_vulkan.py` needs more work.
To proceed, the generator computes a model of Vulkan API based on `vk.xml`
(the file from Kronos describing the API) and then uses a `jinja2` template
to write the file.

Here the basic steps:

 - Load vk.xml
 - Use `xmltodict` to parse the xml document
 - Generate a good data model from it
 - Pass the model to the `vulkan.template.py` file
 - The template engine generate the final Python file

## Community

You can checkout my blog, I speak about *vulkan*:
[Blog](https://realitix.github.io)

## Stay in touch

You can contact me by opening issue (bug or interesting discussion about
the project). If you want a fast and pleasant talk, join the irc channel:
`##vulkan` (I'm realitix). I'm connected from 9AM to 6PM (France).

## History

This module comes from a long journey. I have first created [CVulkan](https://github.com/realitix/cvulkan).
*CVulkan* is a wrapper created in plain C, plain C is hard to maintain... So I have decided to restart with
CFFI which is from far the **best** way to do it. There was a module [pyVulkan](https://github.com/bglgwyng/pyVulkan)
that did what I wanted to do. But it was not working and the code was hard to maintain. I asked to the maintainer
to let me [help him](https://github.com/bglgwyng/pyVulkan/issues/12) but I got no answer.
I forked his project and I rewrote every single part to obtain a good module.

## Supported By

*vulkan* is supported by helpful 3rd parties via code contributions, test devices and so forth.
Make our supporters happy and visit their sites!

![linagora](https://www.linagora.com/sites/all/themes/tux/logo.png)
