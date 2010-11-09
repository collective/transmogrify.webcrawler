
from zope.interface import implements
from zope.interface import classProvides

from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection

from transmogrify.webcrawler.external import webchecker
from transmogrify.webcrawler.external.webchecker import Checker,Page
from transmogrify.webcrawler.external.webchecker import MyHTMLParser,MyStringIO
import re
from htmlentitydefs import entitydefs
import urllib,os, urlparse
from sys import stderr
import urlparse
import logging
logger = logging.getLogger('Plone')
#from interfaces import ISectionFeedback
from zope.annotation.interfaces import IAnnotations


VERBOSE = 0                             # Verbosity level (0-3)
MAXPAGE = 0                        # Ignore files bigger than this
CHECKEXT = False    # Check external references (1 deep)
VERBOSE = 0         # Verbosity level (0-3)
MAXPAGE = 150000    # Ignore files bigger than this
NONAMES = 0         # Force name anchor checking


class WebCrawler(object):
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        try:
            self.feedback = ISectionFeedback(transmogrifier)
        except:
            self.feedback = None
        self.open_url = MyURLopener().open
        self.options = options
        self.ignore_re = [re.compile(pat.strip()) for pat in options.get("ignore",'').split('\n') if pat]


        self.checkext  = options.get('checkext', CHECKEXT)
        self.verbose   = options.get('verbose', VERBOSE)
        self.maxpage   = options.get('maxsize', MAXPAGE)
        self.nonames   = options.get('nonames', NONAMES)
        self.site_url  = options.get('site_url', options.get('url', None))
        self.max = options.get('max',None)
        self.cache = options.get('cache', None)
        self.context = transmogrifier.context
        #self.alias_bases  = [a for a in options.get('alias_bases', '').split() if a]
        # make sure we end with a /
        if self.site_url[-1] != '/':
            self.site_url=self.site_url+'/'
        if os.path.exists(self.site_url):
            self.site_url = 'file://'+urllib.pathname2url(self.site_url)

    def __iter__(self):
        for item in self.previous:
            yield item

        if not self.site_url:
            return

        options = self.options

        def pagefactory(text, url, verbose=VERBOSE, maxpage=MAXPAGE, checker=None):

            try:
                page = LXMLPage(text,url,verbose,maxpage,checker,options)
            except HTMLParseError, msg:
                #msg = self.sanitize(msg)
                ##elf.note(0, "Error parsing %s: %s",
                #          self.format_url(url), msg)
                # Dont actually mark the URL as bad - it exists, just
                # we can't parse it!
                page = None
            return page

        webchecker.Page = pagefactory

        if not self.restoreCache():
            self.checker = MyChecker()
        #self.checker.alias_bases = self.alias_bases
        self.checker.cache = self.cache
        self.checker.site_url = self.site_url

        self.checker.setflags(checkext   = self.checkext,
                         verbose    = self.verbose,
                         maxpage    = self.maxpage,
                         nonames    = self.nonames)

        #must take off the '/' for the crawler to work
        self.checker.addroot(self.site_url[:-1])
        self.checker.sortorder[self.site_url] = 0
        #for root in self.alias_bases:
        #    self.checker.addroot(root, add_to_do = 0)
        #    self.checker.sortorder[root] = 0


        while self.checker.todo:
            if self.max and len(self.checker.done) == int(self.max):
                break
            urls = self.checker.todo.keys()
            #urls.sort()
            del urls[1:]
            for url,part in urls:

                if not url.startswith(self.site_url[:-1]):
                    self.checker.markdone((url,part))
                    msg = "webcrawler: External: %s" %str(url)
                    logger.log(logging.DEBUG, msg)
                    print >> stderr, msg
                    yield dict(_bad_url = url)
                elif [pat for pat in self.ignore_re if pat and pat.search(url)]:
                    self.checker.markdone((url,part))
                    msg = "webcrawler: Ignoring: %s" %str(url)
                    logger.log(logging.DEBUG, msg)
                    print >> stderr, msg
                    yield dict(_bad_url = url)
                else:
                    print >> stderr, "Crawling: "+ str(url)
                    msg = "webcrawler: Crawling: %s" %str(url)
                    logger.log(logging.DEBUG, msg)
                    base = self.site_url
                    self.checker.dopage((url,part))
                    page = self.checker.name_table.get(url) #have to usse unredirected
                    origin = url
                    url = self.checker.redirected.get(url,url)
                    names = self.checker.link_names.get(url,[])
                    path = url[len(self.site_url):]
                    path = '/'.join([p for p in path.split('/') if p])
                    info = self.checker.infos.get(url)
                    file = self.checker.files.get(url)
                    sortorder = self.checker.sortorder.get(origin,0)
                    if info:
                        text = page and page.html() or file
                        item = dict(_path         = path,
                                    _site_url     = base,
                                    _backlinks    = names,
                                    _sortorder    = sortorder,
                                    _content      = text,
                                    _content_info = info,
                                    _orig_path    = path)
                        if origin != url:
                            orig_path = origin[len(self.site_url):]
                            orig_path = '/'.join([p for p in orig_path.split('/') if p])
                            item['_origin'] = orig_path
                        if self.feedback:
                            self.feedback.success('webcrawler',msg)
                        yield item
                    else:
                        msg = "webcrawler: bad_url: %s" %str(url)
                        print >> stderr, msg
                        logger.log(logging.DEBUG, msg)
                        if self.feedback:
                            self.feedback.ignored('webcrawler',msg)
                        yield dict(_bad_url = origin)
        self.storeCache()

    CACHE_KEY = 'funnelweb_cache'
    def restoreCache(self):
        """ get cached pages from annotation and use them instead of recrawling"""
        try:
            checker = IAnnotations(self.context).get('funnelweb.checker')
            options = IAnnotations(self.context).get('funnelweb.options')
        except:
            return False
        if not self.cache or self.options != options:
            return False
        if checker is not None:
            self.checker = checker
            self.checker.resetRun()
            return True
        return False

    def storeCache(self):
        """ get cached pages from annotation and use them instead of recrawling"""
        if not self.cache:
            return
        try:
            IAnnotations(self.context)['funnelweb.checker'] = self.checker
            IAnnotations(self.context)['funnelweb.options'] = self.options
        except:
            return


class MyChecker(Checker):
    link_names = {} #store link->[name]
    def message(self, format, *args):
        pass # stop printing out crap

    def reset(self):
        self.infos = {}
        self.files = {}
        self.redirected = {}
        self.alias_bases = {}
        self.html_cache = {}
        self.sortorder = {}
        self.counter = 0
        Checker.reset(self)

    def __getstate__(self):
        mystate = self.infos, self.files, self.redirected, self.html_cache
        return (Checker.__getstate__(self),mystate)

    def __setstate__(self, state):
        self.reset()
        try:
            cstate,mystate = state
            Checker.__setstate__(self,cstate)
            self.infos, self.files, self.redirected, self.html_cache = mystate
        except:
            pass
        self.resetRun()

    def resetRun(self):
        self.roots = []
        self.todo = {}
        self.done = {}
        self.bad = {}

    def readhtml(self, url_pair):
        if url_pair in self.html_cache:
            return self.html_cache[url_pair]
        else:
            res = Checker.readhtml(self, url_pair)
            self.html_cache[url_pair] = res
            return res


    def openhtml(self, url_pair):
        oldurl, fragment = url_pair

        f = self.openpage(url_pair)
        if f:
            url = f.geturl()
            if url != oldurl:
                self.redirected[oldurl] = url
            self.infos[url] = info = f.info()
            #Incement counter to get ordering of links within pages over whole site
            if not self.checkforhtml(info, url):
                self.files[url] = f.read()
                self.safeclose(f)
                f = None
        else:
            url = oldurl
        return f, url

    def openpage(self, url_pair):
        url, fragment = url_pair
        old_pair = url_pair
        old_url = url
        # actually open alias instead

#        if self.site_url.endswith('/'):
#            realbase=self.site_url[:-1]

#        for a in self.alias_bases:
#            if a.endswith('/'):
#                a=a[:-1]
#            if a and url.startswith(a):
#                base = url[:len(a)]
#                path = url[len(a):]
#                url = realbase+path
#                break

        
        cache = self.cache
        if cache and not url.startswith('file://'):
            cache = cache.rstrip('/')+'/'
            url = cache + url[len(self.site_url):]
            if not url.startswith('file:'):
                url = 'file:'+ url

            try:
                f = self.urlopener.open(url)
                newurl = f.geturl()
                #we need to check if there was a redirection in cache
                newpath = newurl[len(cache):]
                oldpath = old_url[len(self.site_url):]
                diff = newpath[len(oldpath):]
                if diff:
                    f.url = old_url.rstrip('/') + '/' + diff
                else:
                    f.url = old_url
                return f
            except (OSError, IOError), msg:
                pass
        try:
            return self.urlopener.open(old_url)
        except (OSError, IOError), msg:
            msg = self.sanitize(msg)
            self.note(0, "Error %s", msg)
            if self.verbose > 0:
                self.show(" HREF ", url, "  from", self.todo[url_pair])
            self.setbad(old_pair, msg)
            return None
        
    def setSortOrder(self, link):
        """ give each link a counter as it's encountered to later use in sorting """
        if link not in self.sortorder:
            self.sortorder[link] = self.counter
            self.counter = self.counter + 1
            
        



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
        #scheme,netloc,path,parameters,query,fragment = urlparse.urlparse(url)
        path = urllib.url2pathname(url)
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

from lxml import etree
import lxml.html
import lxml.html.soupparser
from lxml.html.clean import Cleaner
from lxml.html.clean import clean_html
import HTMLParser
from HTMLParser import HTMLParseError
from lxml.etree import tostring


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

        if self.maxpage and size > self.maxpage:
            self.note(0, "Skip huge file %s (%.0f Kbytes)", self.url, (size*0.001))
            self.parser = None
            return

        if options:
            text = self.reformat(text, url)
        self.checker.note(2, "  Parsing %s (%d bytes)", self.url, size)
        text = clean_html(text)
        try:
#            self.parser = lxml.html.fromstring(text)
            self.parser = lxml.html.soupparser.fromstring(text)
            self.parser.resolve_base_href()
            self._html = tostring(self.parser,
                                             encoding=unicode,
                                             method="html",
                                             pretty_print=True)
            return
        except UnicodeDecodeError, HTMLParseError:
            pass
        try:
            self.parser = lxml.html.soupparser.fromstring(text)
            self.parser.resolve_base_href()
            self._html = tostring(self.parser,
                                             encoding=unicode,
                                             method="html",
                                             pretty_print=True)
        except HTMLParser.HTMLParseError:
            logger.log(logging.INFO, "webcrawler: HTMLParseError %s"%url)
            raise
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
        #cleaner = Cleaner(page_structure=False, links=False)
        #rhtml = cleaner.clean_html(html)
        return self._html

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
            self.checker.setSortOrder(link)
            #and to filter list
            infos.append((link, rawlink, fragment))

        return infos


    def reformat(self, text, url):
            pattern = self.options.get('patterns','')
            replace = self.options.get('subs','')
            for p,r in zip(pattern.split('\n'),replace.split('\n')):
                if p and r:
                    text,n = re.subn(p,r,text)
                    if n:
                        print >>stderr, "patching %s with %i * %s" % (url,n,p)
            return text

