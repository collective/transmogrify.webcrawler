
from zope.interface import implements
from zope.interface import classProvides
from zope.component import queryUtility
from plone.i18n.normalizer.interfaces import IURLNormalizer

from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection


class Relinker(object):
    classProvides(ISectionBlueprint)
    implements(ISection)
    
    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.locale = getattr(options, 'locale', 'en')
        self.normalize = queryUtility(IURLNormalizer).normalize
    
    def __iter__(self):
        items = []
        for item in self.previous:

            # only handle html/xhtml files 
            if '_path' not in item or \
               '_mimetype' not in item or \
               'text' not in item or \
               item['_mimetype'] not in ['text/xhtml', 'text/html']: 
                yield item; continue
            
            items.append(item)

        changes = []
        for item in items:
            for url_part in self.normalize_path(item['_path']):
                changes.append(url_part)

        new_items = []
        for item in items:
            for change in changes:
                item['text'] = item['text'].replace(change[1], change[0])
                item['_path'] = item['_path'].replace(change[1], change[0])
            new_items.append(item)

        new_items.sort()
        for item in new_items:
            yield item

    def normalize_path(self, path):
        for part in path.split('/')[1:]:
            yield self.normalize(part, self.locale), part
        
