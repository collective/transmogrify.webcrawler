
from zope.interface import implements
from zope.interface import classProvides
from zope.component import queryUtility
from plone.i18n.normalizer.interfaces import IURLNormalizer

from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
import urllib
from lxml import etree
import lxml
from urlparse import urljoin
from external.relative_url import relative_url
from sys import stderr

class Relinker(object):
    classProvides(ISectionBlueprint)
    implements(ISection)
    
    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.locale = getattr(options, 'locale', 'en')
        util = queryUtility(IURLNormalizer)
        if util:
            self.normalize = util.normalize
        else:
            from external.normalize import baseNormalize
            self.normalize = baseNormalize
    
    
    def __iter__(self):
        
        #TODO: needs to take input as to what new name should be so other blueprints can decide
        #TODO: needs allow complete changes to path so can move structure
        #TODO: needs to change file extentions of converted docs. or allow others to change that
        #TODO need to fix relative links 
        

        changes = {}
        for item in self.previous:
            path = item.get('_path',None)
            if not path:
                yield item
                continue
            norm = lambda part: self.normalize(urllib.unquote_plus(part))
            newpath = '/'.join([norm(part) for part in path.split('/')])
            origin = item.get('_origin')
            if not origin:
                origin = item['_origin'] = path
            item['_path'] = newpath
            changes[item.get('_site_url','')+origin] = item                

        for item in changes.values():
            if 'text' in item and item.get('_mimetype') in ['text/xhtml', 'text/html']: 
                path = item['_path']
                oldbase = item['_site_url']+item['_origin']
                newbase = item['_site_url']+path
                def replace(link):
                    #import pdb; pdb.set_trace()
                    linked = changes.get(link)
                    if linked:
                        linkedurl = item['_site_url']+linked['_path']
                        return relative_url(newbase, linkedurl)
                    else:
                        if link.count('html'):
                            pass
                            #print >>stderr, "WARNING: relinker link %s not found from %s"%(link,path) 
                        return relative_url(newbase, link)
                
                try:
                    tree = lxml.html.soupparser.fromstring(item['text'])
                    tree.rewrite_links(replace, base_href=oldbase)
                    item['text'] = etree.tostring(tree,pretty_print=True,encoding="utf8")
                except Exception:
                    print >>stderr, "ERROR: relinker parse error %s, %s" % (path,str(Exception))
                    pass
            del item['_origin']
            #rewrite the backlinks too
            backlinks = item.get('_backlinks',[])
            newbacklinks = []
            for origin,name in backlinks:
                #assume absolute urls
                backlinked= changes.get(origin)
                if backlinked:
                    newbacklinks.append(('/'.join([backlinked['_site_url'],backlinked['_path']]),name))
                else:
                    newbacklinks.append((origin,name))
            if backlinks:
                item['_backlinks'] = newbacklinks                        
                
                
            yield item
        
