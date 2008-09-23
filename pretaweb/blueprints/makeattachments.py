
from zope.interface import classProvides
from zope.interface import implements
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import Condition, Expression
import logging
logger = logging.getLogger('Plone')


"""
Make Attachments
================


Will look at the backlinks for all Images (or other types) and will
make those items subitems of what its linked from if that is the only
place they are linked from.
By default this will turn a Document into a Folder with a defaultview
and place the attachments inside that folder. If you don't want that 
behaviour you can specify field names to use for attachments.

for example

... [attachments]
... blueprint = pretaweb.blueprints.makeattachments
... fields = python:{'attachment'+num+'Title': item['title'], 'attachment'+num+'Image': item['image']}
... condition = python: item.get('_type') in ['Image']

will add attachment1, attachment2 etc fields to the html item.


"""

class MakeAttachments(object):
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.fields=Expression(options.get('fields',''), transmogrifier, name, options)
        self.condition=Condition(options.get('condition',''), transmogrifier, name, options)

    def __iter__(self):

        # split items on subitems and other
        items, subitems = [], {}
        for item in self.previous:
            backlinks = item.get('_backlinks',[])
            #if self.condition(item):
            #    import pdb; pdb.set_trace()
            if len(backlinks) == 1:
                link,name = backlinks[0]
                subitems.setdefault(link, [])
                subitems[link].append(item)
            items.append(item)
 
        #TODO: take care of case where our parent is a subitem

        # apply new fields from subitems to items 
        for item in items:
            base = item.get('_site_url',None)
            path = item.get('_origin',item.get('_path',None))
            if not base or not path:
                yield item
                continue
            #if path.count('safetyproc'):
            #    import pdb; pdb.set_trace()
            #if '_path' in item and item.get('_path','').count('026D.doc'):
            #    import pdb; pdb.set_trace()
            for i, subitem in enumerate(subitems.get(base+path,[])):
                subbase = subitem.get('_site_url',None)
                subpath = subitem.get('_origin',item.get('_path',None))
                if subitems.get(subbase+subpath,[]):
                    # we won't make recursive attachments
                    continue
                if not self.condition(item,i=i+1,subitem=subitem):
                    yield subitem
                    continue
                change = self.fields(item, subitem=subitem, num=i+1)
                if not change:
                    yield subitem
                item.update(dict(change))
                msg = "imakeattachments: %s to %s{%s}" %(subpath,path,dict(change).keys())
                logger.log(logging.DEBUG, msg)
                # now pass a move request to relinker
                file,text=change[0]
                #import pdb; pdb.set_trace()
                newpath = '/'.join(item['_path'].split('/')+[file])
                yield dict(_origin=subpath,
                           _path=newpath,
                           _site_url=subbase)
            if base+path in subitems:
                del subitems[base+path]
            yield item
        #remainder
        for url,items in subitems.items():
#            import pdb; pdb.set_trace()
            
            for item in items:
                yield item




