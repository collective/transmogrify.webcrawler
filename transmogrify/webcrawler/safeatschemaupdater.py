#from zope import event
from zope.interface import classProvides, implements
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import Matcher
from collective.transmogrifier.utils import defaultKeys
import logging
logger = logging.getLogger('Plone')
from interfaces import ISectionFeedback


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
        try:
            self.feedback = ISectionFeedback(transmogrifier)
        except:
            self.feedback = None
        self.secname = name


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

                for key, parts in fields.items():
                    value, arguments = parts

                    field = obj.getField(key)
                    if field is None:
                        continue

                    try:
                        oldvalue = field.get(obj)
                    except Exception,e:
                        msg = "ERROR: _safeatschemaupdater:error %s, %s" %(path,e)
                        logger.log(logging.ERROR, msg, exc_info=True)
                        errors.append(str(e))
                    else:
                        oldvalue = None

                    try:
                        if oldvalue != value:
                            field.set(obj, value, **arguments)
                            changed = True
                            msg = "safeatschemaupdater: updated %s, %s" %(path,(key,arguments))
                            logger.log(logging.DEBUG, msg)
                    except Exception,e:
                        msg = "ERROR: _safeatschemaupdater:error %s, %s" %(path,e)
                        logger.log(logging.ERROR, msg, exc_info=True)
                        errors.append(str(e))
                        continue


                obj.unmarkCreationFlag()
                if errors:
                    item['_safeatschemaupdater:error'] = errors
                    if self.feedback: self.feedback.ignored(self.secname,'')
                else:
                    if self.feedback: self.feedback.success(self.secname,'')


                if is_new_object:
                    #event.notify(ObjectInitializedEvent(obj))
                    obj.at_post_create_script()
                elif changed:
                    #event.notify(ObjectEditedEvent(obj))
                    obj.at_post_edit_script()


            yield item



