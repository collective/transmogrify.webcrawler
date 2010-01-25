#from zope import event
from zope.interface import classProvides, implements
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import Matcher
from collective.transmogrifier.utils import defaultKeys
import urllib
import xmlrpclib
import logging
logger = logging.getLogger('Plone')



from Products.Archetypes.interfaces import IBaseObject
#from Products.Archetypes.event import ObjectInitializedEvent
#from Products.Archetypes.event import ObjectEditedEvent

class RemoteSchemaUpdaterSection(object):
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.context = transmogrifier.context
        self.target = options['target']
        self.target = self.target.rstrip('/')+'/'

        if 'path-key' in options:
            pathkeys = options['path-key'].splitlines()
        else:
            pathkeys = defaultKeys(options['blueprint'], name, 'path')
        self.pathkey = Matcher(*pathkeys)


    def __iter__(self):
        for item in self.previous:

            pathkey = self.pathkey(*item.keys())[0]

            if not pathkey:         # not enough info
                yield item; continue

            path = item[pathkey]
            
            url = urllib.basejoin(self.target, path)
            
            changed = False
            errors = []

            # support field arguments via 'fieldname.argument' syntax
            # result is dict with tuple (value, fieldarguments)
            # stored in fields variable
            fields = {}
            for key, value in item.iteritems():
                if key.startswith('_'):
                    continue
                parts = key.split('.',1)
                fields.setdefault(parts[0], [None,{}])
                if len(parts)==1:
                    fields[parts[0]][0] = value
                else:
                    fields[parts[0]][1][parts[1]] = value
                    
                proxy = xmlrpclib.ServerProxy(url)
                multicall = xmlrpclib.MultiCall(proxy)
                for key, parts in fields.items():
                    value, arguments = parts
                    if type(value) == type(u''):
                        value = value.encode('utf8')

                    #getattr(proxy,'set%s'%key.capitalize())(value)
                    arguments.update(dict(value=value))
                    input = urllib.urlencode(arguments)
                    f = urllib.urlopen(url+'/set%s'%key.capitalize(), input)
                    nurl = f.geturl()
                    info = f.info()
                
                for attempt in range(0,3):
                    try:
                        if '_defaultpage' in item:
                            proxy.setDefaultPage(item['_defaultpage']) 
                        #result = multicall()
                        proxy.update() #does indexing
                        break
                    except xmlrpclib.ProtocolError,e:
                        if e.errcode == 503:
                            continue
                        else:
                            raise


            yield item



