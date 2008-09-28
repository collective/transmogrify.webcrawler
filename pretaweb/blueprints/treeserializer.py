
from zope.interface import implements
from zope.interface import classProvides

from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection

from pretaweb.blueprints.external.webchecker import MyURLopener
import logging
logger = logging.getLogger('Plone')

class TreeSerializer(object):
    classProvides(ISectionBlueprint)
    implements(ISection)
    
    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.default_pages = options.get('default_pages', 'index.html').split()
        self.default_containers = options.get('default_containers', 'Folder').split()

    def __iter__(self):
        items = {}
        for item in self.previous:
            if '_site_url' not in item or \
               '_path' not in item:
                yield item
            else:
                path = item['_path']
                base = item['_site_url']
                if path and path[0] == '/':
                    path = path[1:]
                #if base+path in items:
                #    import pdb; pdb.set_trace()
                items[base+path] = item
        
        # build tree
        items_keys = items.keys()
        items_keys.sort()
        for item in items_keys:
            item_fullurl = item
            item = items[item]
            
            parts = item['_path'].split('/')
            if parts[0] == '':
                parts = parts[1:]

            basepath = ''
            parentpath = ''
            for part in parts:
                basepath += part
                if item['_site_url']+basepath not in items:
                    items[item['_site_url']+basepath] = dict(
                        _path     = basepath,
                        _type     = 'Folder',
                        _site_url = item['_site_url'])
                    msg = "treeserialize: adding folder %s" %(basepath)
                    logger.log(logging.DEBUG, msg)
                    #import pdb; pdb.set_trace()

                elif parts[-1] == part and \
                     part in self.default_pages and \
                     item['_site_url']+parentpath in items and \
                     items[item['_site_url']+parentpath]['_type'] in self.default_containers:
                    items[item['_site_url']+parentpath]['_defaultpage'] = part
                parentpath += basepath
                basepath += '/'

        # has to be in order so they get created
        items_keys = items.keys()
        items_keys.sort()
        #import pdb; pdb.set_trace()
        for item in items_keys:
            yield items[item]


