__author__ = 'dylanjay'

from zope.interface import classProvides, implements
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import defaultKeys
import logging

from ZODB import Connection, DB
from BTrees import OOBTree, IOBTree
from ZODB.FileStorage import FileStorage
import transaction
import cPickle as pickle

_marker = object()

"""
transmogrify.itemcache
=============================

Caches items in a zodb backed file to reduce memory

Options:

:output:
  File to store cached content in

"""

counter = 0


class CacheItem(OOBTree.OOBTree):

    def __getitem__(self, key):
        # during the middle of processing we want to try and upload objects back to storage
        global counter
        if counter % 500 == 0:
            transaction.savepoint(True)
        counter += 1
        return super(CacheItem, self).__getitem__(key)

class CacheItems(object):
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.context = transmogrifier.context

        self.output = options.get('output')
        self.logger = logging.getLogger(name)

        storage = FileStorage(self.output, create=True)
        db = DB(storage, cache_size_bytes=100000000)
        connection = db.open()
        self.root = connection.root()


    def __iter__(self):
        i = 0
        for item in self.previous:
            try:
                pickle.dumps(item)
                cached_item = CacheItem(item)
                self.root[i] = cached_item
                i += 1
                yield cached_item
            except Exception, e:
                # our OpenOnRead cache can't be pickled so we'll just leave those out
                yield item
