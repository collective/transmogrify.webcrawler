from setuptools import setup, find_packages
import os

version = '0.2'

setup(name='transmogrify.webcrawler',
      version=version,
      description="",
      long_description=open(os.path.join("transmogrify", "webcrawler", "webcrawler.txt")).read() + "\n" +
                        open(os.path.join("transmogrify", "webcrawler", "typerecognitor.txt")).read() + "\n" +
                        open(os.path.join("docs", "HISTORY.txt")).read(),
      # Get more strings from http://www.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        ],
      keywords='transmogrifier blueprint funnelweb source plone import conversion microsoft office',
      author='Dylan Jay',
      author_email='software@pretaweb.com',
      url='http://www.pretaweb.com',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['transmogrify'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          # -*- Extra requirements: -*-
          'lxml',
          'BeautifulSoup',
          'collective.transmogrifier',
          ],
      entry_points="""
            [z3c.autoinclude.plugin]
            target = transmogrify
            """,
            )
