
from zope.interface import implements
from zope.interface import classProvides

from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection

from pretaweb.blueprints.external import webchecker
from pretaweb.blueprints.external.webchecker import Checker,Page
from pretaweb.blueprints.external.webchecker import MyHTMLParser
import re
from htmlentitydefs import entitydefs
import urllib,os

#patch webcheckers parser to do entities

def link_attr(self, attributes, *args):
        for name, value in attributes:
            if name in args:
                if value: value = value.strip()
                if value:
                    for entity,repl in entitydefs.items():
                        value = value.replace('&%s;'%entity,repl) 
                    self.links.setdefault(value,[])
                    self.last_link = value

def start_a(self, attributes):
    self.link_attr(attributes, 'href')
    self.check_name_id(attributes)
    if 'href' in [a for a,v in attributes]:
        self.text = ''

def handle_data(self, data):
    text = getattr(self,'text',None)
    if text is not None:
        self.text += data

def end_a(self): 
    last = getattr(self,'last_link',None)
    text = getattr(self,'text',None)
    if last and text:
        text = ' '.join(text.split())
        self.links.setdefault(last,[]).append(text.strip())
    self.last_link = self.text = None

MyHTMLParser.link_attr = link_attr
MyHTMLParser.start_a = start_a
MyHTMLParser.handle_data = handle_data
MyHTMLParser.end_a = end_a


real_getlinkinfos = Page.getlinkinfos 
def getlinkinfos(self):
    infos = real_getlinkinfos(self)
    for link, rawlink, fragment in infos:
            #override to get link text
            names = [(self.url,name) for name in self.parser.links.get(rawlink,[])]
            self.checker.link_names.setdefault(link,[]).extend(names)
    return infos

Page.getlinkinfos = getlinkinfos



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
            link_names = {} #store link->[name]
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
                names = checker.link_names.get(url[0],[])

                # pass preccesed files
                if url[0].startswith(self.site_url):
                    file_path = url[0][len(self.site_url):]
                    if file_path:
                        if checker.last_info:
#                            content = self.open_url(self.site_url+file_path)
                            yield dict(_path         = file_path,
                                       _site_url     = self.site_url,
                                       _backlinks    = names,
                                       _content      = checker.last_text,
                                       _content_info = checker.last_info,)
                        else:
                            yield dict(_bad_url = self.site_url+file_path)
                            continue
                else:
                    yield dict(_bad_url = url[0])


class MyURLopener(urllib.FancyURLopener):

    http_error_default = urllib.URLopener.http_error_default

    def __init__(*args):
        self = args[0]
        apply(urllib.FancyURLopener.__init__, args)
        self.addheaders = [
            ('User-agent', 'Transmogrifier-crawler/0.1'),
            ]

    def http_error_401(self, url, fp, errcode, errmsg, headers):
        return None

    def open_file(self, url):
        path = urllib.url2pathname(urllib.unquote(url))
        if os.path.isdir(path):
            if path[-1] != os.sep:
                url = url + '/'
            for index in ['index.html','index.htm','index_html']:
                indexpath = os.path.join(path, index)
                if os.path.exists(indexpath):
                    return self.open_file(url + index)
            try:
                names = os.listdir(path)
            except os.error, msg:
                exc_type, exc_value, exc_tb = sys.exc_info()
                raise IOError, msg, exc_tb
            names.sort()
            s = MyStringIO("file:"+url, {'content-type': 'text/html'})
            s.write('<BASE HREF="file:%s">\n' %
                    urllib.quote(os.path.join(path, "")))
            for name in names:
                q = urllib.quote(name)
                s.write('<A HREF="%s">%s</A>\n' % (q, q))
            s.seek(0)
            return s
        return urllib.FancyURLopener.open_file(self, url)
            
webchecker.MyURLopener = MyURLopener