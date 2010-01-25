from zope.interface import classProvides, implements
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import defaultMatcher

from Acquisition import aq_base
from Products.CMFCore.utils import getToolByName
import xmlrpclib
import urllib
from urlparse import urlparse, urljoin
import logging
logger = logging.getLogger('Plone')

class RemoteConstructorSection(object):
    classProvides(ISectionBlueprint)
    implements(ISection)
    
    "Drop in replacement for constructor that will use xmlprc calls to construct content on a remote plone site"

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.context = transmogrifier.context
        #self.ttool = getToolByName(self.context, 'portal_types')

        self.typekey = defaultMatcher(options, 'type-key', name, 'type',
                                      ('portal_type', 'Type'))
        self.pathkey = defaultMatcher(options, 'path-key', name, 'path')
        self.target = options.get('target','http://localhost:8080/plone')
        self.target = self.target.rstrip('/')+'/'

    def __iter__(self):
        basepath = xmlrpclib.ServerProxy(self.target).getPhysicalPath()
        for item in self.previous:
            keys = item.keys()
            typekey = self.typekey(*keys)[0]
            pathkey = self.pathkey(*keys)[0]

            if not (typekey and pathkey):             # not enough info
                yield item; continue

            type_, path = item[typekey], item[pathkey]

            #fti = self.ttool.getTypeInfo(type_)
            #if fti is None:                           # not an existing type
            #    msg = "constructor: no type found %s:%s" % (type_,path)
            #    logger.log(logging.ERROR, msg)
            #    yield item; continue

            elems = path.strip('/').rsplit('/', 1)
            
            for attempt in range(0, 3):
                try:
                
                    url = urllib.basejoin(self.target, path)
                    proxy = xmlrpclib.ServerProxy(url)
                    container, id = (len(elems) == 1 and ('', elems[0]) or elems)
                    #if id == 'index.html':
                    try:
                        #test paths in case of acquition
                        rpath = proxy.getPhysicalPath()
                        rpath = rpath[len(basepath):]
                        if path == '/'.join(rpath):
                            break
                    except xmlrpclib.Fault:
                        pass
                    purl = urllib.basejoin(self.target,container)
                    pproxy = xmlrpclib.ServerProxy(purl)
                    try:
                        pproxy.invokeFactory(type_, id)
                    except xmlrpclib.ProtocolError,e:
                        if e.errcode == 302:
                            pass
                        else:
                            raise
                    break
                except xmlrpclib.ProtocolError,e:
                    if e.errcode == 503:
                        continue
                    else:
                        raise
            
            yield item
            
