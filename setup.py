from setuptools import setup, find_packages
import os
import re

version = '1.2.1'


def docstring(file):
    py = open(os.path.join("transmogrify", "webcrawler", file)).read()
    return re.findall('"""(.*?)"""', py, re.DOTALL)[0]


setup(name='transmogrify.webcrawler',
      version=version,
      description="Crawling and feeding html content into a transmogrifier pipeline",
      long_description=open('README.rst').read() + '\n' +
                        docstring('webcrawler.py') + \
                        docstring('staticcreator.py') + \
                        docstring('typerecognitor.py') + \
#                      open(os.path.join("transmogrify", "webcrawler", "webcrawler.txt")).read() + "\n" +
#                        open(os.path.join("transmogrify", "webcrawler", "typerecognitor.txt")).read() + "\n" +
                        '\n'+ open(os.path.join("docs", "HISTORY.txt")).read(),
      # Get more strings from http://www.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        ],
      keywords='transmogrifier blueprint funnelweb source plone import conversion microsoft office',
      author='Dylan Jay',
      author_email='software@pretaweb.com',
      url='http://github.com/collective/transmogrify.webcrawler',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['transmogrify'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          # -*- Extra requirements: -*-
          'lxml',
          'beautifulsoup4',
          'collective.transmogrifier',
          ],
      entry_points="""
            [z3c.autoinclude.plugin]
            target = transmogrify
            """,
            )
