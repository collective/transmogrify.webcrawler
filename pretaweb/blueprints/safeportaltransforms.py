
import fnmatch
from zope.interface import classProvides
from zope.interface import implements
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
import shutil
from plone.app.transmogrifier.portaltransforms import PortalTransformsSection

# monkey patch to ignore errors due to some weird windows timing thing
from Products.PortalTransforms.libtransforms.commandtransform import commandtransform
def cleanDir(self, tmpdir):
    try:
        shutil.rmtree(tmpdir, ignore_errors=True)
    except OSError:
        pass
commandtransform.cleanDir = cleanDir



class SafePortalTransforms(PortalTransformsSection):
    classProvides(ISectionBlueprint)
    implements(ISection)



    def __init__(self, transmogrifier, name, options, previous):
        PortalTransformsSection.__init__(self, transmogrifier, name, options, previous)
        if not getattr(self,'from_',None):
            self.from_field = options.get('mimetype_field')
            assert self.from_field, "either from_ or mimetype_field must be set"

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
                        # we get Illegal html errorrs etc sometimes
                        continue
                else:
                    from_ = self.from_ or item[self.from_field] 
                    try:
                        data = self.ptransforms.convertToData(
                                                              self.target, item[key], mimetype=from_)
                    except:
                        continue
                    #TODO: we should be able to get images etc too
                    #for sub in data.getSubObjects():

                    #    yield dict(_type='Image',
                    #               _path='/'.join([item['_path'],sub['name']]),
                    #               data=sub)
                    item[key] = str(data)
                    if self.from_field:
                        item[self.from_field] = self.target
                                                
            yield item


