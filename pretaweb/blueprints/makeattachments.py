
from zope.interface import classProvides
from zope.interface import implements
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import Condition, Expression


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
            backlinks = item.get('_backlinks',{})
            if len(backlinks) == 1 and self.condition(item):
                subitems.setdefault(backlinks.keys()[0], [])
                subitems[backlinks.keys()[0]].append(item)
            else:
                items.append(item)

        # apply new fields from subitems to items 
        for item in items:
            fullurl = item.get('_site_url','') + item.get('_path','')
            if subitems.get(fullurl, None):
                for i, subitem in enumerate(subitems[fullurl]):
                    item.update(self.fields(item, subitem=subitem, num=i))
            yield item




