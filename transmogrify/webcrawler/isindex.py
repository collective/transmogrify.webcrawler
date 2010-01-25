
import fnmatch
from zope.interface import classProvides
from zope.interface import implements
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import Matcher

from lxml import etree
import lxml.html
import lxml.html.soupparser

from StringIO import StringIO
from sys import stderr
import logging
logger = logging.getLogger('Plone')



class IsIndex(object):
    classProvides(ISectionBlueprint)
    implements(ISection)



    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.min_links=options.get('min_links',2)
        self.max_uplinks=options.get('max_uplinks',2)
            

    def __iter__(self):
      
        #Stri
      
                    
        self.moved= {}
        items = {}
        ulinks = {}
        for item in self.previous:
            path,html = self.ishtml(item)
            if not path:
                yield item
                continue
            
            tree = lxml.html.fragment_fromstring(html)
            base = item.get('_site_url','')
            tree.make_links_absolute(base+path)
            if '_origin' in item:
                self.moved[item['_origin']] = path
            links = []
            items[path] = (item,path,links)
            for element, attribute, link, pos in tree.iterlinks():
                if attribute == 'href' and link not in ulinks:
                    ulinks[link] = True
                    if link.startswith(base):
                        link = link[len(base):]
                    link = '/'.join([p for p in link.split('/') if p])
                    links.append(link)
        done = []
        while items:
            indexes = {}
            for item,path,links in items.values():
                if not links:
                    continue
                count, dir, rest = self.indexof(links)
                print >>stderr, (count,len(links),dir,path,item.get('_template'), rest)
                if self.isindex(count,links):
                    indexes.setdefault(dir,[]).append((count,item,path,links,dir))
    
            mostdeep = [(len(dir.split('/')),i) for dir,i in indexes.items()]
            if not mostdeep:
                break
            mostdeep.sort()
            depth,winner = mostdeep[-1]
            self.move(winner)
            for count,item,path,links,dir in winner:
                del items[path]
                yield item
        for item,path,links in items.values():
            yield item
                    
                
                     
    def move(self, items):
        if not items: return
        items.sort()
        count,item,toppath,links,dir = items[-1]
        for count,item,path,links,dir in items:
            if False: #path == toppath: #TODO need a better way to work out default view
                file = 'index_html'
            else:
                file = path.split('/')[-1]
            
            if dir:
                target = dir+'/'+file
            else:
                target = file
            if item['_path'] == target:
                continue
            item.setdefault('_origin',path)
            item['_path'] = target
                
            self.moved[path] = item['_path']
            msg = "isindex: moved %s to %s" %(path,dir+'/'+file)
            logger.log(logging.DEBUG, msg)

    def isindex(self, count, links):
        return count >= self.min_links and count>=len(links)-self.max_uplinks
            

    def indexof(self, links):
        dirs = {}
        def most(count):
            return self.isindex(count,links)

        for link in links:
            newlink = self.moved.get(link)
            if newlink:
                link = newlink
                
            dir = '/'.join([p for p in link.split('/') if p][:-1])
            dirs[dir] = dirs.get(dir,0) + 1
        if not dirs:
            return 0,None
        alldirs = dirs
        while True:
            tops = [(count,dir) for dir,count in dirs.items()]
            tops.sort()
            count,dir = tops[-1]
            if most(count) or len(tops)<2:
                break
            #find common dir. Take longest and make it shorter
            common = [(dir,count) for count,dir in tops]
            common.sort()
            common.reverse()
            longdir,longcount = common[0]
            longdir = '/'.join(longdir.split('/')[:-1])
            dirs = dict(common[1:])
            dirs[longdir] = dirs.get(longdir,0) + longcount
            
        return count,dir, alldirs
    
#            tops = []
#            found = False
#            for dir,count in common[1:]:
#                if not found and longdir.startswith(dir) and dir:
#                    count = count+longcount
#                    found = True
#                tops.append((count,dir))


    def ishtml(self, item):
              path = item.get('_path',None)
              content = item.get('_content',None) or item.get('text',None)
              mimetype = item.get('_mimetype',None)
              if  path and content and mimetype in ['text/xhtml', 'text/html']:
                  return path,content
              else:
                  return None,None
       
