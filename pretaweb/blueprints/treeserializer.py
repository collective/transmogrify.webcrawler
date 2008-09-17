
from zope.interface import implements
from zope.interface import classProvides

from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection

from pretaweb.blueprints.external.webchecker import MyURLopener


class TreeSerializer(object):
    classProvides(ISectionBlueprint)
    implements(ISection)
    
    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.open_url = MyURLopener().open



    def __iter__(self):
        dirsdone = {}
        for item in self.previous:
            if '_site_url' not in item or '_path' not in item:
                yield item
                continue
            #import pdb; pdb.set_trace()
            path = item['_path']
            site_url = item['_site_url']
            parts = [p for p in path.split('/') if p][:-1]
            for i in range(1,len(parts)+1):
                folder = '/'.join(parts[:i])
                if not folder in dirsdone:
                    yield dict(_path=folder, _type='Folder', _site_url = site_url)
                    dirsdone[folder] = True
            if path in dirsdone:
                # won't always work unless we sort the paths first
                
                name = 'index_html'
                newpath = '/'.join([p for p in path.split('/') if p]+[name])
                #item['_path'] = newpath
                yield item
                #yield dict(_path=path,_defaultpage=name)
            else:
                yield item
                
            




    def old__iter__(self):
        item_list = {}
        for item in self.previous:
            if '_site_url' not in item or \
               '_path' not in item:
                yield item
            else:
                item_list[item['_path']] = item
                site_url = item['_site_url']
        
        # build tree
        tree = {}
        top_object = None
        item_list_paths = item_list.keys()
        item_list_paths.sort()
        #import pdb; pdb.set_trace()
        for item in item_list_paths:
            # path should be defined as absolute
            path = item_list[item]['_path'] 
            #import pdb; pdb.set_trace()
            object_list = [p for p in path.split('/') if p]
            
            def set_object(tree, object, sub_objects):
                tree.setdefault(object, {})
                if len(sub_objects) != 0:
                    tree[object] = set_object(tree[object], 
                                              sub_objects[0], 
                                              sub_objects[1:])
                return tree
            tree.update(set_object(tree, object_list[0], object_list[1:]))
            #print object_list
        
        # serialize tree
        def tree_serializer(tree, path):
            for object in tree:
                # create full url and check for page
                if path+object not in item_list:
                    # this is a folder
                    item_list[path+object] = dict(_path     = path+object,
                                                  _type     = 'Folder',
                                                  _site_url = site_url)
                if len(tree[object]) != 0:
                    tree_serializer(tree[object], path+object+'/')
        tree_serializer(tree, '/')

        # first page
        if '/' in item_list:
            for front_page in ['/front-page', '/index_html', '/first-page']:
                if front_page not in item_list:
                    item_list[front_page] = item_list['/']
                    item_list[front_page]['_type'] = 'Page'
                    item_list['/'] = dict(_path        = '/',
                                          _type        = None,
                                          _defaultpage = front_page)

        item_list_paths = item_list.keys()
        item_list_paths.sort()
        #print path_list
        for item in item_list_paths:
            yield item_list[item]
            


