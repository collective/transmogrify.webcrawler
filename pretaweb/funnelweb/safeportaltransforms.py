
import fnmatch
from zope.interface import classProvides
from zope.interface import implements
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
import shutil
from plone.app.transmogrifier.portaltransforms import PortalTransformsSection
from sys import stderr
from relinker import relinkHTML
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
            newitem = item.copy()
            for key in item:
                match = self.keys(key)[1]
                if not (match and self.condition(item, key=key, match=match)):
                    continue
                if self.transform:
                    try:
                        newitem[key] = self.ptransforms(self.transform, item[key])
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
                        newitem[self.destination] = str(data)
                        del newitem[key]
                    else:
                        newitem[key] = str(data)
                    if self.from_field:
                        newitem[self.from_field] = self.target
                    if hasattr(data,'getSubObjects'):
                        
                        
                        tmp = item['_path'].split('/')
                        base = tmp[:-1]
                        doc_id = tmp[-1]
                        origin = item.get('_origin',item.get('_path')).split('/')

                        #because the names of subobjects aren't unique we have to 
                        #move it to a folder
                        folder = dict(_type='Folder',
                                   _path=item['_path'],
                                   _site_url=item.get('_site_url'),
                                   _default_page=doc_id)
                        #Need to move the folder as moving html screws the links
                        if '_origin' in item:
                            folder['_origin'] = item.get('_origin')
                            del newitem['_origin']
                        yield folder

                        #newitem['_origin'] = item.get('_origin',item['_path'])
                        newitem['_path'] = item['_path']+'/'+doc_id
                        
                        base = item.get('_site_url')
                        changes = {}

                        for name,data in data.getSubObjects().items():
                            #TODO: maybe shouldn't hard code this
                            subpath = '/'.join(tmp+[name])
                            subitem = {'_type':           'Image',
                                   #'_origin':         '/'.join(origin+[name]),
                                   '_path':           subpath,
                                   '_site_url':       base,
                                   '_backlinks':      [(base+newitem['_path'],'')],
                                   'image':           data,
                                   'image.filename':  name}
                            yield subitem

            yield newitem



