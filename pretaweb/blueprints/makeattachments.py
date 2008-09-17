
import fnmatch
from zope.interface import classProvides
from zope.interface import implements
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import Matcher

from webstemmer.analyze import PageFeeder, LayoutAnalyzer
from webstemmer.zipdb import ACLDB
from lxml import etree
import lxml.html
import lxml.html.soupparser

from StringIO import StringIO
from sys import stderr


"""
Make Attachments
================


Will look at the backlinks for all Images (or other types) and will
make those items subitems of what its linked from if that is the only
place they are linked from.
By default this will turn a Document into a Folder with a defaultview
and place the attachments inside that folder. If you don't want that 
behaviour you can specify field names to use for attachments.

for example

... [attachments]
... blueprint = pretaweb.blueprints.makeattachments
... attachmentfields = python: ['attachment'+str(i) for i in range(1,5) if 'attachment'+str(i) not in item.keys()
... condition = python: item.get('_type') in ['Image']

will add attachment1, attachment2 etc fields to the html item.


"""

class IsIndex(object):
    classProvides(ISectionBlueprint)
    implements(ISection)



    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.fields=options.get('attachmentfields',None)
        self.condition=options.get('condition',None)
            

    def __iter__(self):
      
        #Stri
      
        items = []
        tomerge = {}
        for item in self.previous:
            back = item.get('_backlinks',{})
            if len(back) == 1:
                tomerge.setdefault(back.keys()[0],[]).append(item)
            else:
                items.append(item)
        for item in items:
            url = item.get('_site_url','') + item.get('_path','')
            subs = tomerge(url)
            if not self.fields:
                dir = self.makefolder(item)
                yield dir
                for sub in subs:
                    self.move(sub,item)
                    yield sub
            else:
                for sub in subs:
                    self.move(sub,item,self.fields(item))
            yield item
                
                     
 