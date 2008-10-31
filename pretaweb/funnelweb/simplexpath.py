

from lxml import etree
from StringIO import StringIO

from zope.interface import implements
from zope.interface import classProvides
from zope.component import queryUtility

from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection


class SimpleXPath(object):
    classProvides(ISectionBlueprint)
    implements(ISection)
    
    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.xpath = options.get('xpath')
        self.key = options.get('key')
        self.from_key = options.get('from_key', self.key)
    
    def __iter__(self):
        for item in self.previous:
            
            if self.from_key not in item or \
               not item[self.from_key] or \
               '_mimetype' not in item or \
               item['_mimetype'] not in ['text/xhtml', 'text/html']: 
                yield item; continue
           
            parser = etree.XMLParser(recover=True)
            tree = etree.parse(StringIO(item[self.from_key]), parser)
            result = tree.xpath(self.xpath)
            if len(result) == 0:
                yield item; continue

            item[self.key] = result[0].text
            yield item

