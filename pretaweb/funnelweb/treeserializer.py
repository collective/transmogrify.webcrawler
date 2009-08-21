
from zope.interface import implements
from zope.interface import classProvides

from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection

from pretaweb.funnelweb.external.webchecker import MyURLopener
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
                items[base+path] = item

        # build tree
        items_keys = items.keys()
        items_keys.sort()
        for item in items_keys:
            item_fullurl = item
            item = items[item]

            parts = item['_path'].split('/')
#            if parts[0] == '':
#                parts = parts[1:]

            basepath = ''
            parentpath = ''
            parent = items.get(item['_site_url'])
            for part in parts:
                basepath += part

                if item['_site_url']+basepath in items:
                    #case where folder has text
                    if parent and parent.get('text', None) is not None:
                        # move to default page and replace with folder
                        parentpath = parent['_path'].split('/')
                        for i in ['']+range(1,10000):
                            newname = "%s%s"%(self.default_pages[0],i)
                            newpath = '/'.join([p for p in parentpath+[newname] if p])
                            if item['_site_url']+newpath not in items:
                                break
                        parent['_path'] = newpath
                        items[item['_site_url']+newpath] = parent
                        parentpath = '/'.join([p for p in parentpath if p])
                        newparent = dict(
                                            _path     = parentpath,
                                            _site_url = item['_site_url'],
                                            _defaultpage = newname)
                        if basepath != '':
                            newparent['_type'] = self.default_containers[0]
                        else:
                            #special case for portal object
                            pass
                        items[item['_site_url']+parentpath] = newparent

                        msg = "treeserialize: moved folder to %s" %(parent['_path'])
                        logger.log(logging.DEBUG, msg)
                else:
                    # parent which hasn't had a folder added yet
                    newparent = dict(
                        _path     = basepath,
                        _type     = self.default_containers[0],
                        _site_url = item['_site_url'])
                    items[item['_site_url']+basepath] = newparent
                    msg = "treeserialize: adding folder %s" %(basepath)
                    logger.log(logging.DEBUG, msg)
                if basepath != item['_path']:
                    parent = items.get(item['_site_url']+basepath)
                    basepath += '/'

            #case item is a default page
            if parts and parent and parent.get('_defaultpage') is None and \
                parts[-1] in self.default_pages and \
                parent.get('_type') in self.default_containers:
                    parent['_defaultpage'] = parts[-1]






        # has to be in order so they get created
        items_keys = items.keys()
        items_keys.sort()
        for item in items_keys:
            yield items[item]


