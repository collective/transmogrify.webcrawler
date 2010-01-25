
from zope.interface import classProvides
from zope.interface import implements
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import Condition, Expression
import logging
logger = logging.getLogger('Plone')



class MakeAttachments(object):
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.fields=Expression(options.get('fields','python:False'), transmogrifier, name, options)
        self.condition=Condition(options.get('condition','python:True'), transmogrifier, name, options)
        self.defaultpage = options.get('defaultpage','index-html')

    def __iter__(self):

        # split items on subitems and other
        items, subitems = [], {}
        for item in self.previous:
            backlinks = item.get('_backlinks',[])
            if len(backlinks) == 1:
                link,name = backlinks[0]
                subitems.setdefault(link, [])
                subitems[link].append(item)
            items.append(item)
 
        # apply new fields from subitems to items 
        total = 0
        merged = 0
        for item in items:
            base = item.get('_site_url',None)
            origin = item.get('_origin',item.get('_path',None))
            if not base or not origin:
                yield item
                continue
            links = subitems.get(base+origin,[])
            backlinks =  item.get('_backlinks',[])
            if not links and len(backlinks)==1 and subitems.get(backlinks[0][0]) is not None:
                continue #item is a deadend and will be delt with elsewhere
            folder=None
            i = 0
            attach = []
            for subitem in links:
                subbase = subitem.get('_site_url',None)
                suborigin = subitem.get('_origin',subitem.get('_path',None))
                    
                if subitems.get(subbase+suborigin,[]):
                    # subitem isn;t a deadend and will be dealt with elsewhere. 
                    continue
                if not self.condition(item,i=i,subitem=subitem):
                    yield subitem
                    continue
                change = self.fields(item, subitem=subitem, i=i)
                if change:
                    item.update(dict(change))
                    msg = "imakeattachments: %s to %s{%s}" %(suborigin,origin,dict(change).keys())
                    logger.log(logging.DEBUG, msg)
                    # now pass a move request to relinker
                    file,text=change[0]
                    attach.append(dict(_origin=suborigin,
                               _path=file,
                               _site_url=subbase))
                else: #turn into default folder
                    if not folder:
                        folder = dict(_path=item['_path'],
                                      _site_url=base,
                                      _type="Folder",
                                      _defaultpage=self.defaultpage)
                        if not item.get('_origin'):
                            item['_origin']=item['_path']
                        item['_path'] = '/'.join(item['_path'].split('/') + [self.defaultpage])
                    if '_origin' not in subitem:
                        subitem['_origin'] = subitem['_path']
                    file = subitem['_path'].split('/')[-1]
                    subitem['_path'] = '/'.join(folder['_path'].split('/') + [file])
                    yield subitem
                i = i +1
            if folder:
                yield folder
            yield item
            # got to set actual final paths of attachments moves
            for subitem in attach:
                subitem['_path'] = '/'.join(item['_path'].split('/')+[subitem['_path']])
                yield subitem
                
        

        

