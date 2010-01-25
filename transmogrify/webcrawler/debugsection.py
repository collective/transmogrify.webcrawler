
import fnmatch
from zope.interface import classProvides
from zope.interface import implements
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import Matcher

from lxml import etree
import lxml.html
import lxml.html.soupparser

from StringIO import StringIO
from sys import stderr
import logging
logger = logging.getLogger('Plone')
from sys import stderr


"""
Debug logging on what is passing through

"""

allitems = []

class DebugSection(object):
    classProvides(ISectionBlueprint)
    implements(ISection)



    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.name = None
        self.secname = name
        last = None
        for i,section in enumerate(options):
            if section == self:
                break
            self.name = last
            last = section
            

    def __iter__(self):
      
        i = 0
        pos = len(allitems)
        items = {}
        allitems.append(items)
        
        for item in self.previous:
            items.setdefault(item.get('_path'),[]).append(item)
            if item.get('_path'):
                msg = "debugsection: got %s" %(item.get('_path'))
                #logger.log(logging.DEBUG, msg)
                #print >> stderr, msg
            yield item
            i = i + 1

        if pos > 0:
            for path in allitems[pos-1]:
                if path not in items: 
                    print >> stderr, "lost %s"%path
                    
        msg = "debugsection: %s, %i items" %(self.secname,i)
        logger.log(logging.DEBUG, msg)
        print >> stderr, msg
                     
