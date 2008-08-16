from setuptools import setup, find_packages
import os

version = '1.0'

setup(name='pretaweb.blueprints',
      version=version,
      description="",
      long_description=open("README.txt").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      # Get more strings from http://www.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        ],
      keywords='transmogrifier blueprint source plone import conversion microsoft office',
      author='Rok Garbas',
      author_email='rok.garbas@gmail.com',
      url='git://git.plone.si/~rok/pretaweb.blueprints.git',
      license='Private',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['pretaweb'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          # -*- Extra requirements: -*-
          'collective.transmogrifier',
          'plone.app.transmogrifier',
          ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
