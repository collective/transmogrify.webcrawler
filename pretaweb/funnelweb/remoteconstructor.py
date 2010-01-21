from zope.interface import classProvides, implements
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import defaultMatcher

from Acquisition import aq_base
from Products.CMFCore.utils import getToolByName
import xmlrpclib
import urllib
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

    def __iter__(self):
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
            
            url = urllib.basejoin(self.target, path)
            f = urllib.urlopen(url)
            nurl = f.geturl()
            info = f.info()
            html = f.read()
            if "Please double check the web address" not in html:
                yield item
                continue
            
            container, id = (len(elems) == 1 and ('', elems[0]) or elems)
            url = urllib.basejoin(self.target,container)
            input =  urllib.urlencode({'type_name':type_,
                'id':id
                }
               )
            f = urllib.urlopen("%s/invokeFactory" % url, input)
            nurl = f.geturl()
            info = f.info()
            res = f.read()

            yield item
