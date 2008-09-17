
import fnmatch
from zope.interface import classProvides
from zope.interface import implements
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import Matcher
from urllib import unquote,quote



class PathMover(object):
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        moves = options.get('moves')
        self.moves = []
        for line in moves.strip().split('\n'):
            line = [t for t in line.strip().split('\t') if t]
            if len(line)>1:
                self.moves.append(('%s/'%line[0],'%s/'%('/'.join(line[1:]))))
            elif len(line) == 1:
                self.moves.append(('','%s/'%line[0]))

    def __iter__(self):
        #import pdb; pdb.set_trace()       
        items = []
        for item in self.previous:
            self.move(item)
            
            yield item

    def move(self, item):
        path = item.get('_path')
        if not path:
            return None
        path = unquote(path)
        #if path.count('Information'):
        #    import pdb; pdb.set_trace()
        for origin,target in self.moves:
            if not target:
                continue
            origin = unquote(origin)
            if path==origin[:-1] or path.startswith(origin):
                newpath = target+path[len(origin):]
                if not item.get('_origin'):
                    item['_origin'] = item.get('_path')
                #import pdb; pdb.set_trace()
                item['_path'] = quote(newpath)
                return
        
        