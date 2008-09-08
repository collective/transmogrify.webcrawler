
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
            if item_list[item]['_path'][0:1] == '/' and \
                 item_list[item]['_path'] != '/':
                object_list = item_list[item]['_path'].split('/')[1:]
                # remove last character if its ''
                # this happens when url end with /
                if object_list[-1] == '':
                    del object_list[-1]
                
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
            


