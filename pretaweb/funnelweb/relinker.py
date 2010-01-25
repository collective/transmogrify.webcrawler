
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
from collective.transmogrifier.utils import Expression
import logging
from external.normalize import urlnormalizer as normalizer
import urlparse
logger = logging.getLogger('Plone')
from sys import stderr
#from plone.i18n.normalizer import urlnormalizer as normalizer

INVALID_IDS = ['security']


class Relinker(object):
    classProvides(ISectionBlueprint)
    implements(ISection)
    
    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.locale = getattr(options, 'locale', 'en')
        self.link_expr = None
        if options.get('link_expr', None):
            self.link_expr = Expression(
                    options['link_expr'],
                    transmogrifier, name, options)
        #util = queryUtility(IURLNormalizer)
        #if util:
        #    self.normalize = util.normalize
        #else:
        self.locale = Expression(options.get('locale', 'python:None'), 
                                transmogrifier, name, options)
        
    
    
    def __iter__(self):
        
        #TODO: needs to take input as to what new name should be so other blueprints can decide
        #TODO: needs allow complete changes to path so can move structure
        #TODO: needs to change file extentions of converted docs. or allow others to change that
        #TODO need to fix relative links 
        

        changes = {}
        bad = {}
        for item in self.previous:
            path = item.get('_path',None)
            if not path:
                url = item.get('_bad_url')
                if url:
                    bad[url] = item
                yield item
                continue
            base = item.get('_site_url','')
            
            def norm(part):
                #TODO - don't normalize to existing names
                if part[0] == '_':
                    part = part[1:]+'-1'
                # Get the information we require for normalization
                keywords = dict(text=urllib.unquote_plus(part), locale=self.locale(item))
                # Perform Normalization
                part = normalizer.normalize(**keywords)
                if part in INVALID_IDS:
                    return part+'-1'
                else:
                    return part 
            newpath = '/'.join([norm(part) for part in path.split('/')])
            origin = item.get('_origin')
            if not origin:
                origin = item['_origin'] = path
            item['_path'] = newpath
            #normalize link
            link = urllib.unquote_plus(base+origin)
            #assert not changes.get(link,None), str((item,changes.get(base+origin,None)))
                
            changes[link] = item

        for item in changes.values():
            if 'text' in item and item.get('_mimetype') in ['text/xhtml', 'text/html']:
                relinkHTML(item, changes, bad, link_expr=self.link_expr)
            del item['_origin']
            #rewrite the backlinks too
            backlinks = item.get('_backlinks',[])
            newbacklinks = []
            for origin,name in backlinks:
                #assume absolute urls
                backlinked= changes.get(origin)
                if backlinked:
                    backlink = backlinked['_site_url']+backlinked['_path']
                    newbacklinks.append((backlink,name))
                else:
                    newbacklinks.append((origin,name))
            if backlinks:
                item['_backlinks'] = newbacklinks
    
            yield item

def relinkHTML(item, changes, bad={}, link_expr=None):        
    path = item['_path']
    oldbase = item['_site_url']+item['_origin']
    newbase = item['_site_url']+path
    def swapfragment(link, newfragment):
        t = urlparse.urlparse(link)
        fragment = t[-1]
        t = t[:-1] + (newfragment,)
        link = urlparse.urlunparse(t)
        return link, fragment
    
    def replace(link):
        link, fragment = swapfragment(link, '')

        linked = changes.get(link)
        if not linked:
            link = urllib.unquote_plus(link)
            linked = changes.get(link)
            
        if linked:
            if link_expr:
                linkedurl = item['_site_url']+link_expr(linked)
            else:
                linkedurl = item['_site_url']+linked['_path']
            return swapfragment(relative_url(newbase, linkedurl), fragment)[0]
        else:
            #if path.count('commercial-part-codes.doc'):
            if link not in bad:
                msg = "relinker: no match for %s in %s" % (link,path)
                logger.log(logging.DEBUG, msg)
                print >> stderr, msg
            return swapfragment(relative_url(newbase, link), fragment)[0]
    
    tree = lxml.html.fragment_fromstring(item['text'])
    tree.rewrite_links(replace, base_href=oldbase)
    item['text'] = etree.tostring(tree,pretty_print=True,encoding=unicode)
 #   except Exception:
 #       msg = "ERROR: relinker parse error %s, %s" % (path,str(Exception))
 #       logger.log(logging.ERROR, msg, exc_info=True)
