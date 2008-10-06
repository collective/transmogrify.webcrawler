
from zope.interface import implements
from zope.interface import classProvides

from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection

from pretaweb.blueprints.external import webchecker
from pretaweb.blueprints.external.webchecker import Checker,Page
from pretaweb.blueprints.external.webchecker import MyHTMLParser,MyStringIO
import re
from htmlentitydefs import entitydefs
import urllib,os
from sys import stderr
from lxml import etree
import lxml.html
import lxml.html.soupparser
from lxml.html.clean import Cleaner
import urlparse
import logging
logger = logging.getLogger('Plone')

VERBOSE = 0                             # Verbosity level (0-3)
MAXPAGE = 0                        # Ignore files bigger than this
CHECKEXT = True    # Check external references (1 deep)
VERBOSE = 0         # Verbosity level (0-3)
MAXPAGE = 150000    # Ignore files bigger than this
NONAMES = 0         # Force name anchor checking


class WebCrawler(object):
    classProvides(ISectionBlueprint)
    implements(ISection)
    
    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.open_url = MyURLopener().open
        self.options = options
        self.ignore_re = [re.compile(pat.strip()) for pat in options.get("ignore",'').split('\n') if pat]
        

        self.checkext  = options.get('checkext', CHECKEXT)
        self.verbose   = options.get('verbose', VERBOSE)
        self.maxpage   = options.get('maxpage', MAXPAGE)
        self.nonames   = options.get('nonames', NONAMES)
        self.site_url  = options.get('site_url', None)
        self.alias_bases  = [a for a in options.get('alias_bases', '').split() if a]
        # make sure we end with a / 
        if self.site_url[-1] != '/':
            self.site_url=self.site_url+'/'

    def __iter__(self):
        for item in self.previous:
            yield item

        if not self.site_url:
            return
        
        options = self.options
        infos = {}
        files = {}
        redirected = {}
        alias_bases = self.alias_bases
        site_url = self.site_url

        class MyChecker(Checker):
            link_names = {} #store link->[name]
            def message(self, format, *args):
                pass # stop printing out crap

            
            def openhtml(self, url_pair):
                oldurl, fragment = url_pair
                                
                f = self.openpage(url_pair)
                if f:
                    url = f.geturl()
                    if url != oldurl:
                        redirected[oldurl] = url
                    infos[url] = info = f.info()
                    if not self.checkforhtml(info, url):
                        files[url] = f.read()
                        self.safeclose(f)
                        f = None
                else:
                    url = oldurl
                return f, url
                    
            def openpage(self, url_pair):
                url, fragment = url_pair
                old_pair = url_pair
                # actually open alias instead
                realbase = site_url
                if site_url.endswith('/'):
                    realbase=site_url[:-1]
                if url.count('random'):
                            import pdb; pdb.set_trace()

                for a in [realbase]: #+alias_bases:
                    if a.endswith('/'):
                        a=a[:-1]
                    if a and url.startswith(a):
                        base = url[:len(a)]
                        path = url[len(a):]
                        url = realbase+path
                        break
                
                try:
                    return self.urlopener.open(url)
                except (OSError, IOError), msg:
                    msg = self.sanitize(msg)
                    self.note(0, "Error %s", msg)
                    if self.verbose > 0:
                        self.show(" HREF ", url, "  from", self.todo[url_pair])
                    self.setbad(old_pair, msg)
                    return None

        def pagefactory(text, url, verbose=VERBOSE, maxpage=MAXPAGE, checker=None):
            return LXMLPage(text,url,verbose,maxpage,checker,options)

        webchecker.Page = pagefactory
        
        checker = MyChecker()
        checker.setflags(checkext   = self.checkext, 
                         verbose    = self.verbose,
                         maxpage    = self.maxpage, 
                         nonames    = self.nonames)

        #must take off the '/' for the crawler to work
        checker.addroot(self.site_url[:-1])
        for root in self.alias_bases:
            checker.addroot(root, add_to_do = 0)


        #import pdb; pdb.set_trace()
        while checker.todo:
            urls = checker.todo.keys()
            urls.sort()
            del urls[1:]
            #import pdb; pdb.set_trace()
            for url,part in urls:
                if self.ignore(url):
                    checker.markdone((url,part))
                    print >> stderr, "Ignoring: "+ str(url)
                    msg = "webcrawler: Ignoring: %s" %str(url)
                    logger.log(logging.DEBUG, msg)
                    yield dict(_bad_url = url)
                else:
                    print >> stderr, "Crawling: "+ str(url)
                    msg = "webcrawler: Crawling: %s" %str(url)
                    logger.log(logging.DEBUG, msg)
                    base = self.site_url
                    checker.dopage((url,part))
                    page = checker.name_table.get(url) #have to usse unredirected
                    origin = url
                    url = redirected.get(url,url)
                    names = checker.link_names.get(url,[])
                    path = url[len(self.site_url):]
                    path = '/'.join([p for p in path.split('/') if p])
                    #if path.count('file'):
                    #    import pdb; pdb.set_trace()
                    info = infos.get(url)
                    file = files.get(url)
                    if info:
                        text = page and page.html() or file
                        item = dict(_path         = path,
                                       _site_url     = base,
                                       _backlinks    = names,
                                       _content      = text,
                                       _content_info = info,)
                        if origin != url:
                            item['_origin'] = origin
                        yield item
                    else:
                        #if path.count('abrv'):
                        #    import pdb; pdb.set_trace()
                        msg = "webcrawler: bad_url: %s" %str(url)
                        print >> stderr, msg
                        logger.log(logging.DEBUG, msg)
                        yield dict(_bad_url = origin)

    def ignore(self, url):
#        if not url.startswith(self.site_url[:-1]):
#            return True
        for pat in self.ignore_re:
            if pat and pat.search(url):
                return True
        return False

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


# do tidy and parsing and links via lxml. also try to encode page properly
class LXMLPage:

    def __init__(self, text, url, verbose=VERBOSE, maxpage=MAXPAGE, checker=None, options=None):
        self.text = text
        self.url = url
        self.verbose = verbose
        self.maxpage = maxpage
        self.checker = checker
        self.options = options

        # The parsing of the page is done in the __init__() routine in
        # order to initialize the list of names the file
        # contains. Stored the parser in an instance variable. Passed
        # the URL to MyHTMLParser().
        size = len(self.text)
        #import pdb; pdb.set_trace()

        if self.maxpage and size > self.maxpage:
            self.note(0, "Skip huge file %s (%.0f Kbytes)", self.url, (size*0.001))
            self.parser = None
            return
        
        if options:
            text = self.reformat(text, url)
        self.checker.note(2, "  Parsing %s (%d bytes)", self.url, size)
        self.parser = lxml.html.soupparser.fromstring(text)
#        MyHTMLParser(url, verbose=self.verbose,
#                                   checker=self.checker)
#        self.parser.feed(self.text)

    def note(self, level, msg, *args):
        pass

    # Method to retrieve names.
    def getnames(self):
        #if self.parser:
        #    return self.parser.names
        #else:
            return []
        
    def html(self):
        if self.parser is None:
            return ''
        html = etree.tostring(self.parser, encoding="utf8", method="html",pretty_print=True)
        #cleaner = Cleaner(page_structure=False, links=False)
        #rhtml = cleaner.clean_html(html)
        return html

    def getlinkinfos(self):
        # File reading is done in __init__() routine.  Store parser in
        # local variable to indicate success of parsing.

        # If no parser was stored, fail.
        if self.parser is None: return []

        base = urlparse.urljoin(self.url, self.parser.base_url or "")
        infos = []
        for element, attribute, rawlink, pos in self.parser.iterlinks():
            t = urlparse.urlparse(rawlink)
            # DON'T DISCARD THE FRAGMENT! Instead, include
            # it in the tuples which are returned. See Checker.dopage().
            fragment = t[-1]
            t = t[:-1] + ('',)
            rawlink = urlparse.urlunparse(t)
            link = urlparse.urljoin(base, rawlink)
            if link[-1] == '/':
                link = link[:-1]
            #override to get link text
            if attribute == 'href':
                name = ' '.join(element.text_content().split())
                self.checker.link_names.setdefault(link,[]).extend([(self.url,name)])
            elif attribute == 'src':
                name = element.get('alt','')
                self.checker.link_names.setdefault(link,[]).extend([(self.url,name)])
            #and to filter list
            infos.append((link, rawlink, fragment))

        return infos

            
    def reformat(self, text, url):
            pattern = self.options.get('patterns','')
            replace = self.options.get('subs','')
            #import pdb; pdb.set_trace()
            for p,r in zip(pattern.split('\n'),replace.split('\n')):
                if p and r:
                    text,n = re.subn(p,r,text)
                    if n:
                        print >>stderr, "patching %s with %i * %s" % (url,n,p)
            return text

