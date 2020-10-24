from setuptools import setup


with open("README.md") as file:
    long_description = file.read()


setup(
    name='vulkan',
    version='1.1.99.1',
    description='Ultimate Python binding for Vulkan API',
    author='realitix',
    author_email='realitix@gmail.com',
    packages=['vulkan'],
    long_descripiton=long_description,
    long_description_content_type="text/markdown",
    include_package_data=True,
    install_requires=['cffi>=1.10'],
    setup_requires=['cffi>=1.10'],
    url='https://github.com/realitix/vulkan',
    keywords='Graphics,3D,Vulkan,cffi',
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: Android",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Natural Language :: English",
        "Topic :: Multimedia :: Graphics",
        "Topic :: Scientific/Engineering",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    cffi_modules=["vulkan/vulkan_build.py:ffi"]
)
