<p align="center">
<img src="https://cdn.rawgit.com/realitix/vulkan/182062bc/logo/cvulkan-180x180.png" />
</p>

# Vulkan

> The ultimate Python binding for Vulkan API

## Presentation

*vulkan* is a Python extension which supports the Vulkan API. It leverages power of Vulkan with simplicity of Python.
It's a complete Vulkan wrapper, it keeps the original Vulkan API and try to limit differences induced by Python.

*vulkan* is compatible with Python 2 and 3 but please use Python 3 !

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

To understand how to use this wrapper, you must look into `example/example.py` or
refer to [Vulk](https://github.com/realitix/vulk) engine.


## How to contribute

To contribute, you should first read the `Architecture` section.
Any contribution is welcome and I answer quickly.


## Architecture

*vulkan* is a CFFI module generated by a Python script.

When you install this module, you need two files:

- `_cffi_build/vulkan.cdef.h` containing CFFI definitions
- `vulkan/__init__.py` containing the actual executed Python script

Theses two files are generated by the `generator/generate.py` script.

`_cffi_build/vulkan.cdef.h` is generated with a `cpp` command call, it applies pre-processing to the Vulkan C header.
It can't work as is because of `pycparser` which cannot parse the output. That's the purpose of `fake_libc_include` folder.

`vulkan/__init__.py` needs more work.
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