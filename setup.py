#!/usr/bin/env python

import sys, os
from setuptools import setup
import flickr

setup(
    name='python-flickr',
    version=flickr.__version__,
    install_requires=['httplib2', 'oauth2', 'simplejson'],
    author='Mike Helmick',
    author_email='mikehelmick@me.com',
    license='MIT License',
    url='https://github.com/michaelhelmick/python-flickr/',
    keywords='python flickr oauth api',
    description='A Python Library to interface with Flickr REST API & OAuth',
    long_description=open('README.md').read(),
    download_url="https://github.com/michaelhelmick/python-flickr/zipball/master",
    py_modules=["flickr"],
    classifiers = [
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Communications :: Chat',
        'Topic :: Internet'
    ]
)