
from zope.interface import implements
from zope.interface import classProvides
from zope.component import queryUtility
from plone.i18n.normalizer.interfaces import IURLNormalizer

from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
import urllib


class Relinker(object):
    classProvides(ISectionBlueprint)
    implements(ISection)
    
    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.locale = getattr(options, 'locale', 'en')
        util = queryUtility(IURLNormalizer)
        if util:
            self.normalize = util.normalize
        else:
            from external.normalize import baseNormalize
            self.normalize = baseNormalize
    
    
    def __iter__(self):
        
        #TODO: needs to take input as to what new name should be so other blueprints can decide
        #TODO: needs allow complete changes to path so can move structure
        #TODO: needs to change file extentions of converted docs. or allow others to change that 
        
        items = []
        for item in self.previous:
            items.append(item)

        changes = []
        for item in items:
            for url_part in self.normalize_path(item.get('_path','')):
                changes.append(url_part)

        new_items = []
        for item in items:
            for change in changes:
               if item.get('_mimetype') in ['text/xhtml', 'text/html']: 
                    item['text'] = item['text'].replace(change[1], change[0])
               if '_path' in item:
                    item['_path'] = item['_path'].replace(change[1], change[0])
            new_items.append(item)

        new_items.sort()
        for item in new_items:
            yield item

    def normalize_path(self, path):
        for part in path.split('/')[1:]:
            yield self.normalize(urllib.unquote_plus(part)), part
        
