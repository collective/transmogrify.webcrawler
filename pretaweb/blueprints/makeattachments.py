
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
        self.fields=Expression(options.get('fields',''), transmogrifier, name, options)
        self.condition=Condition(options.get('condition','python:True'), transmogrifier, name, options)

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
            if not subitems.get(base+path,[]):
                continue #item is a deadend and will be delt with elsewhere
            folder=None
            i = 0
            for subitem in subitems.get(base+path,[]):
                subbase = subitem.get('_site_url',None)
                subpath = subitem.get('_origin',subitem.get('_path',None))
                    
                if subitems.get(subbase+subpath,[]):
                    # subitem isn;t a deadend and will be dealt with elsewhere. 
                    continue
                if not self.condition(item,i=i,subitem=subitem):
                    yield item
                    continue
                change = self.fields(item, subitem=subitem, i=i)
                #import pdb; pdb.set_trace()
                if change:
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
                else: #turn into default folder
                    if not folder:
                        folder = dict(_path=item['_path'],
                                      _site_url=base,
                                      _type="Folder",
                                      _defaultpage='index_html')
                        if not item.get('_origin'):
                            item['_origin']=path
                        item['_path'] = '/'.join(item['_path'].split('/') + ['index_html'])
                    if '_origin' not in subitem:
                        subitem['_origin'] = subitem['_path']
                    file = subitem['_path'].split('/')[-1]
                    subitem['_path'] = '/'.join(folder['_path'].split('/') + [file])
                    yield subitem
                i = i +1
            if folder:
                yield folder
            yield item

        

