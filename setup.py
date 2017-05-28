from setuptools import setup


setup(
    name='vulkan',
    version='1.0.49',
    description='Ultimate Python binding for Vulkan API',
    author='realitix',
    author_email='realitix@gmail.com',
    packages=['_cffi_build', 'vulkan'],
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
    cffi_modules=["_cffi_build/vulkan_build.py:ffi"]
)
