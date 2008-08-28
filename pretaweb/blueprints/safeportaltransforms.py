
import fnmatch
from zope.interface import classProvides
from zope.interface import implements
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection

from plone.app.transmogrifier.portaltransforms import PortalTransformsSection

class SafePortalTransforms(PortalTransformsSection):
    classProvides(ISectionBlueprint)
    implements(ISection)



    def __init__(self, transmogrifier, name, options, previous):
        PortalTransformsSection.__init__(self, transmogrifier, name, options, previous)
        if not self.from_:
            self.from_field = options.get('from_field')

    def __iter__(self):
        for item in self.previous:
            for key in item:
                match = self.keys(key)[1]
                if not (match and self.condition(item, key=key, match=match)):
                    continue
                if self.transform:
                    try:
                        item[key] = self.ptransforms(self.transform, item[key])
                    except:
                        pass
                else:
                    if not self.from_:
                        from_ = item[self.from_field]
                    else:
                        from_ = self.from_ 
                    import pdb; pdb.set_trace()
                    data = self.ptransforms.convertToData(
                        self.target, item[key], mimetype=from_)
                    for sub in data.getSubObjects():

                        yield dict(_type='Image',
                                   _path='/'.join([item['_path'],sub['name']]),
                                   data=sub)
                    item[key] = data.getData()                        
            yield item


