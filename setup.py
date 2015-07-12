import re

from codecs import open
from distutils.core import setup

version = ''
license = ''
title = ''
author = ''
contact = ''
with open('pymmrouting/__init__.py', 'r') as fd:
    file_content = fd.read()
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
                        file_content, re.MULTILINE).group(1)
    license = re.search(r'^__license__\s*=\s*[\'"]([^\'"]*)[\'"]',
                        file_content, re.MULTILINE).group(1)
    title = re.search(r'^__title__\s*=\s*[\'"]([^\'"]*)[\'"]',
                        file_content, re.MULTILINE).group(1)
    author = re.search(r'^__author__\s*=\s*[\'"]([^\'"]*)[\'"]',
                        file_content, re.MULTILINE).group(1)
    contact = re.search(r'^__contact__\s*=\s*[\'"]([^\'"]*)[\'"]',
                        file_content, re.MULTILINE).group(1)

setup(name=title,
      version=version,
      description="""Python implementation of multimodal routing engine
                     based on multimodal shortest path algorithm for
                     postgis library (libmmspa4pg)""",
      author=author,
      author_email=contact,
      license=license,
      packages=['pymmrouting'])
