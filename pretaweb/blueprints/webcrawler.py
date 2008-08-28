
from zope.interface import implements
from zope.interface import classProvides

from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection

from pretaweb.blueprints.external import webchecker
from pretaweb.blueprints.external.webchecker import Checker
from pretaweb.blueprints.external.webchecker import MyURLopener,MyHTMLParser
import re
from htmlentitydefs import entitydefs

#patch webcheckers parser to do entities

def link_attr(self, attributes, *args):
        for name, value in attributes:
            if name in args:
                if value: value = value.strip()
                if value:
                    for entity,repl in entitydefs.items():
                        value = value.replace('&%s;'%entity,repl) 
                    self.links[value] = None

MyHTMLParser.link_attr = link_attr


class WebCrawler(object):
    classProvides(ISectionBlueprint)
    implements(ISection)
    
    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.open_url = MyURLopener().open
        self.options = options
        
        CHECKEXT = False    # Check external references (1 deep)
        VERBOSE = 0         # Verbosity level (0-3)
        MAXPAGE = 150000    # Ignore files bigger than this
        ROUNDSIZE = 50      # Number of links processed per round
        NONAMES = 0         # Force name anchor checking

        self.checkext  = options.get('checkext', CHECKEXT)
        self.verbose   = options.get('verbose', VERBOSE)
        self.maxpage   = options.get('maxpage', MAXPAGE)
        self.roundsize = options.get('roundsize', ROUNDSIZE)
        self.nonames   = options.get('nonames', NONAMES)
        self.site_url  = options.get('site_url', None)

    def __iter__(self):
        for item in self.previous:
            yield item

        if not self.site_url:
            return
        
        options = self.options

        class MyChecker(Checker):
            def readhtml(self, url_pair):
                url, fragment = url_pair
                self.last_text = text = None
                f, url = self.openhtml(url_pair)
                if f:
                    text = f.read()
                    rtext = self.reformat(text,url)
                    if text != rtext:
                        pass
                    self.last_text = text = rtext
                    f.close()
                return text, url
            
            def openhtml(self, url_pair):
                url, fragment = url_pair
                f = self.openpage(url_pair)
                self.last_info = None
                if f:
                    url = f.geturl()
                    self.last_info = info = f.info()
                    if not self.checkforhtml(info, url):
                        self.last_text = f.read()
                        self.safeclose(f)
                        f = None
                return f, url
            
            def reformat(self, text, url):
                pattern = options.get('patterns','')
                replace = options.get('subs','')
                #import pdb; pdb.set_trace()
                for p,r in zip(pattern.split('\n'),replace.split('\n')):
                    if p and r:
                        text,n = re.subn(p,r,text)
                return text
                

        
        checker = MyChecker()
        checker.setflags(checkext   = self.checkext, 
                         verbose    = self.verbose,
                         maxpage    = self.maxpage, 
                         roundsize  = self.roundsize,
                         nonames    = self.nonames)
        checker.addroot(self.site_url)

        while checker.todo:
            urls = checker.todo.keys()
            urls.sort()
            del urls[1:]
            for url in urls:
                checker.dopage(url)

                # pass preccesed files

                if url[0].startswith(self.site_url):
                    file_path = url[0][len(self.site_url):]
                    if file_path:
                        if checker.last_info:
#                            content = self.open_url(self.site_url+file_path)
                            yield dict(_path         = file_path,
                                       _site_url     = self.site_url,
                                       _content      = checker.last_text,
                                       _content_info = checker.last_info,)
                        else:
                            yield dict(_bad_url = self.site_url+file_path)
                            continue
                        #self.close_handler(content)
                else:
                    yield dict(_bad_url = url[0])
            
        # there are also bad links (files)
#        for file in checker.bad:
#            yield dict(_bad_url = file[0], info=file)

    def close_handler(self, f):
        try:
            url = f.geturl()
        except AttributeError:
            pass
        else:
            if url[:4] == 'ftp:' or url[:7] == 'file://':
                # Apparently ftp connections don't like to be closed
                # prematurely...
                text = f.read()
        f.close()
