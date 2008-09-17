
import fnmatch
from zope.interface import classProvides
from zope.interface import implements
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
import shutil
from plone.app.transmogrifier.portaltransforms import PortalTransformsSection
from sys import stderr
import logging
logger = logging.getLogger('Plone')

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
        self.destination = options.get('destination')
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
                        raise
                        continue
                else:
                    from_ = self.from_ or item[self.from_field]
                    conversion = "%s %s->%s %i" % \
                    (item['_path'],from_,self.target,len(item[key]))
                    
                    try:
                        data = self.ptransforms.convertTo(self.target, item[key], mimetype=from_)
                    except:
                        msg = "ERROR: Failed to convert %s" % conversion
                        logger.log(logging.ERROR, msg, exc_info=True)
                        #raise
                        continue
                    if data is None:
                        message = "ERROR: 0 bytes converting %s" % conversion
                        logger.log(logging.ERROR, message)
                        continue
                    msg = "Converted: %s->%i" % (conversion,len(str(data)))
                    logger.log(logging.DEBUG, msg)
                    if self.destination:
                        item[self.destination] = str(data)
                        del item[key]
                    else:
                        item[key] = str(data)
                    if self.from_field:
                        item[self.from_field] = self.target
                    if hasattr(data,'getSubObjects'):
                        tmp = item['_path'].split('/')
                        base = '/'.join(tmp[:-1])
                        doc_id = tmp[-1]
                        for name,data in data.getSubObjects().items():
                            #TODO: maybe shouldn't hard code this
                            yield {'_type':           'Image',
                                   '_origin':         name,
                                   '_path':           '/'.join([base,doc_id+'-'+name]),
                                   '_site_url':       item.get('_site_url'),
                                   'image':           data,
                                   'image.filename':  name}
                                                
            yield item



