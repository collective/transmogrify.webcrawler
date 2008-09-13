#from zope import event
from zope.interface import classProvides, implements
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import Matcher
from collective.transmogrifier.utils import defaultKeys

from Products.Archetypes.interfaces import IBaseObject
#from Products.Archetypes.event import ObjectInitializedEvent
#from Products.Archetypes.event import ObjectEditedEvent

#####################################################
# from plone.app.transmogrifier
# Override in order to swollow exceptions in updating
#####################################################

class SafeATSchemaUpdaterSection(object):
    classProvides(ISectionBlueprint)
    implements(ISection)
    
    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.context = transmogrifier.context
        
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
            
            obj = self.context.unrestrictedTraverse(path.lstrip('/'), None)
            if obj is None:         # path doesn't exist
                yield item; continue
            
            if IBaseObject.providedBy(obj):
                changed = False
                is_new_object = obj.checkCreationFlag()
                errors = []
                fields = {}
                for k,v in item.iteritems():
                    if k.startswith('_'):
                        continue
                    #support field arguments via field.arg syntax
                    import pdb; pdb.set_trace()
                    parts = k.split('.',1)
                    v,args = fields.setdefault(parts[0],(None,{}))
                    if len(parts)>1:
                        args[parts[1]] = v
                    else:
                        fields[parts[0]] = (v,args)
                for k,pair in fields.items():
                    import pdb; pdb.set_trace()
                    v,args = pair
                    field = obj.getField(k)
                    if field is None:
                        continue
                    try:
                        oldvalue = field.get(obj)
                    except Exception,e:
                        from sys import stderr
                        print >>stderr,"ERROR: _safeatschemaupdater:error %s, %s" %(path,e)
                        errors.append(str(e))
                    else:
                        oldvalue = None
                    try:
                        if oldvalue != v:
                            field.set(obj, v,**args)
                            changed = True
                    except Exception,e:
                        from sys import stderr
                        print >>stderr,"ERROR: _safeatschemaupdater:error %s, %s" %(path,e)
                        errors.append(str(e))
                        continue
                obj.unmarkCreationFlag()
                if errors:
                    item['_safeatschemaupdater:error'] = errors
                
                if is_new_object:
                    #event.notify(ObjectInitializedEvent(obj))
                    obj.at_post_create_script()
                elif changed:
                    #event.notify(ObjectEditedEvent(obj))
                    obj.at_post_edit_script()
            
            yield item
