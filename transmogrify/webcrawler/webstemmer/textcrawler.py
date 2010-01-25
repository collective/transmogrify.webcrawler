#!/usr/bin/env python
#
# textcrawler.py
#
#  Copyright (c) 2005-2006  Yusuke Shinyama <yusuke at cs dot nyu dot edu>
#
#  Permission is hereby granted, free of charge, to any person
#  obtaining a copy of this software and associated documentation
#  files (the "Software"), to deal in the Software without
#  restriction, including without limitation the rights to use,
#  copy, modify, merge, publish, distribute, sublicense, and/or
#  sell copies of the Software, and to permit persons to whom the
#  Software is furnished to do so, subject to the following
#  conditions:
#
#  The above copyright notice and this permission notice shall be
#  included in all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY
#  KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
#  WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
#  PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
#  COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
#  OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
#  SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

# BUGS: only one starturl.

import sys, re, time, socket
from htmlparser3 import HTMLParser3, HTMLHandler
from httplib import HTTPConnection, BadStatusLine
from robotparser import RobotFileParser
from gzip import GzipFile
from cookielib import MozillaCookieJar
from urllib import addinfourl
from urllib2 import Request
from urlparse import urlsplit, urljoin
from zipdb import ACLDB, ZipDumper, NullDumper

stderr = sys.stderr

MAX_PAGE_LEN = 1000000 # 1MB max

try:
  from cStringIO import StringIO
except ImportError:
  from StringIO import StringIO

#from bsddb import hashopen as dbmopen

#from threading import Thread

REMOVE_NAME = re.compile(r'#.*$')
def wash_url(url):
  return REMOVE_NAME.sub('', url.strip().encode('ascii', 'replace'))


class CrawlerWarning(RuntimeError): pass
class CrawlerPageError(RuntimeError): pass
class CrawlerFatalError(RuntimeError): pass


##  URLDB
##
class URLDB:

  def __init__(self, path, debug=0):
#    self.db = dbmopen(path, 'c')
    self.debug = debug
    if self.debug:
      print >>stderr, 'URLDB open: %r' % path
    return

  def visited(self, url):
    import md5, struct
    k = md5.md5(url).digest()
    v = self.db.has_key(k)
    self.db[k] = struct.pack('<L', int(time.time()))
    if self.debug and not v:
      print >>stderr, 'URLDB added: %r' % url
    return v


##  SimpleCrawler
##
class SimpleCrawler:

  USER_AGENT = 'SimpleCrawler/0.1'
  HEADERS = {
    'User-Agent': USER_AGENT,
    'Accept-Encoding': 'gzip',
    'Connection': 'keep-alive'
    }
  CONTENT_TYPE_PAT = re.compile(r'([^\s;]+)(.*charset=([^\s;]+))?', re.I)

  def __init__(self, starturl, index_html='', maxlevel=1,
               cookie_file=None, acldb=None, urldb=None, default_charset=None,
               delay=0, timeout=300, debug=0):
    (proto, self.hostport, _x, _y, _z) = urlsplit(starturl)
#    assert proto == 'http'
    #Thread.__init__(self)
    self.debug = debug
    self.index_html = index_html
    if cookie_file:
      self.cookiejar = MozillaCookieJar(cookie_file)
      self.cookiejar.load()
    else:
      self.cookiejar = None
    self.robotstxt = RobotFileParser()
    self.robotstxt.set_url(urljoin(starturl, '/robots.txt'))
    try:
        self.robotstxt.read()
    except IOError:
        pass
    self.conn = None
    self.urldb = urldb
    self.acldb = acldb
    self.curlevel = 0
    self.delay = delay
    self.timeout = timeout
    self.default_charset = default_charset
    if starturl.endswith('/'):
      starturl += self.index_html
    self.urls = [(starturl, maxlevel)]
    self.crawled = {}                   # 1:injected, 2:crawled
    return

  def accept_url(self, url):
    if url.endswith('/'):
      url += self.index_html
    if self.acldb and not self.acldb.allowed(url):
      return None
    return url

  def inject_url(self, url):
    if (not self.curlevel) or (not url) or (url in self.crawled): return False
    if not self.robotstxt.can_fetch(self.USER_AGENT, url):
      if self.debug:
        print >>stderr, 'DISALLOW: %r' % url
      return None
    if self.debug:
      print >>stderr, 'INJECT: %r' % url
    self.crawled[url] = 1
    self.urls.append((url, self.curlevel-1))
    return True

  def get1(self, url, maxretry=3, maxredirect=3):
    if self.debug:
      print >>stderr, 'GET: %r' % url
    # loop
    for rtry in range(maxredirect):
      # forge urllib2.Request object.
      req = Request(url)
      # add cookie headers if necessary.
      if self.cookiejar:
        self.cookiejar.add_cookie_header(req)
        headers = req.unredirected_hdrs
        headers.update(self.HEADERS)
      else:
        headers = self.HEADERS
      # get response.
      for ctry in range(maxretry):
        try:
          if not self.conn:
            print >>stderr, 'Making connection: %r...' % (self.hostport,)
            self.conn = HTTPConnection(self.hostport)
          self.conn.request('GET', req.get_selector().replace(' ',''), '', headers)
	  self.conn.sock.settimeout(self.timeout)
          resp = self.conn.getresponse()
          break
        except BadStatusLine, x:
          # connection closed unexpectedly
          print >>stderr, 'Connection closed unexpectedly.'
          # it restarts the connection...
          self.conn.close()
          self.conn = None
        except socket.error, x:
          # connection closed unexpectedly
          print >>stderr, 'Socket error:', x
          self.conn.close()
          self.conn = None
      else:
        raise CrawlerFatalError('Maximum retry limit reached: %r' % url)
      # read the page at once (for some reason specifying read(n) causes errors.)
      buf = resp.read()
      if MAX_PAGE_LEN < len(buf):
        raise CrawlerPageError('Too long page (>%dbytes): %r' % (MAX_PAGE_LEN, url))
      # interpret the encoding.
      if 'gzip' in resp.getheader('Content-Encoding', '').lower():
        fp = GzipFile(fileobj=StringIO(buf))
      else:
        fp = StringIO(buf)
      # get cookie received.
      if self.cookiejar:
        r = addinfourl(fp, resp.msg, url)
        r.code = resp.status
        self.cookiejar.extract_cookies(r, req)
      # check the result code.
      status = resp.status
      if status in (301, 302):
        url0 = urljoin(url, resp.getheader('Location', ''))
        url1 = self.accept_url(url0)
        if url1 and (url1 not in self.crawled or self.crawled[url1] != 2):
          print >>stderr, 'REDIRECTED: Status=%d: %r' % (status, url1)
          url = url1
          continue
        else:
          raise CrawlerWarning('Status=%d: Ignore redirect: %r' % (status, url0))
      # mark this as crawled.
      self.crawled[url] = 2
      if status == 200: break      # everything is okay.
      if status != 200:
        raise CrawlerPageError('Status=%d: Error: %r' % (status, url))
    else:
      raise CrawlerPageError('Maximum redirection limit reached: %r' % url)
    # got it.
    return (fp, resp.getheader('Content-Type', 'text/plain'))

  def parse1(self, fp, url, mimetype, charset, visited):
    raise NotImplementedError

  def crawl1(self):
    if self.delay:
      time.sleep(self.delay)
    (url, level) = self.urls.pop()
    if self.debug:
      print >>stderr, 'CRAWL(%d): %r' % (level, url)
    visited = (self.urldb and self.urldb.visited(url))
    if visited:
      print >>stderr, 'VISITED: %r' % url
      self.crawled[url] = 2
    if visited and level == 0: return
    try:
      (fp, filetype) = self.get1(url)
      m = self.CONTENT_TYPE_PAT.match(filetype)
      if m:
        (mimetype, charset) = (m.group(1), m.group(3) or self.default_charset)
      else:
        (mimetype, charset) = (filetype, self.default_charset)
      self.curlevel = level
      self.parse1(fp, url, mimetype, charset, visited)
      fp.close()
    except (CrawlerWarning,CrawlerPageError), x:
      print >>stderr, 'WARNING:', x
    except socket.error, x:
      print >>stderr, 'SOCKET_ERROR:', x
      self.conn.close()
      self.conn = None
    return

  def run(self):
    while self.urls:
      self.crawl1()
      if self.debug:
        print >>stderr, 'URLS_LEFT: %d' % len(self.urls)
      else:
        stderr.write('.'); stderr.flush()
    return


##  RefTextDB
##
class RefTextDB:

  def __init__(self, baseid):
    self.baseid = baseid
    self.dic = {}
    return

  def add(self, name, s):
    if name not in self.dic: self.dic[name] = []
    self.dic[name].append(s)
    return

  def dump(self):
    fp = StringIO()
    for (name,strs) in self.dic.iteritems():
      fp.write(repr( (self.baseid+name, strs) ))
      fp.write('\n')
    return fp.getvalue()


##  HTMLLinkFinder
##
class HTMLLinkFinder(HTMLHandler):

  def __init__(self, crawler, base_href, reftxtdb=None):
    self.crawler = crawler
    self.base_href = base_href
    self.anchor_href = None
    self.anchor_text = []
    self.in_comment = False
    self.reftxtdb = reftxtdb
    return

  def start_base(self, _, attrs):
    attrs = dict(attrs)
    if 'href' in attrs:
      self.base_href = urljoin(self.base_href, wash_url(attrs['href']))
    return

  def start_a(self, _, attrs):
    attrs = dict(attrs)
    if 'href' in attrs:
      url = self.crawler.accept_url(urljoin(self.base_href, wash_url(attrs['href'])))
      if url:
        self.crawler.inject_url(url)
        self.anchor_href = url
        self.anchor_text = []
    return

  def end_a(self, _):
    if self.reftxtdb and self.anchor_href:
      s = ''.join(self.anchor_text)
      if s and self.anchor_href.startswith('http://'):
        self.reftxtdb.add(self.anchor_href[6:], s)
    self.anchor_href = None
    self.anchor_text = []
    return

  start_area = start_a
  end_area = end_a

  def start_comment(self, _, attrs):
    self.in_comment = True
    return
  def end_comment(self, _):
    self.in_comment = False
    return

  def handle_data(self, data):
    if self.anchor_href and not self.in_comment:
      self.anchor_text.append(data)
    return

  def start_unknown(self, tag, attrs):
    return
  def end_unknown(self, tag):
    return
  def do_unknown(self, tag, attrs):
    return
  def finish(self):
    return


##  TextCrawler
##
class TextCrawler(SimpleCrawler):

  ACCEPT_TYPE = ('text/html', 'text/xhtml')

  def __init__(self, consumer, starturl, baseid, reftxtdb=None,
               index_html='', maxlevel=1, cookie_file=None,
               acldb=None, urldb=None, default_charset=None,
               delay=0, timeout=300, debug=0):
    SimpleCrawler.__init__(self, starturl, index_html, maxlevel,
                           cookie_file, acldb, urldb, default_charset, delay, timeout, debug)
    self.consumer = consumer
    self.baseid = baseid
    self.reftxtdb = reftxtdb
    return

  def parse1(self, fp, url, mimetype, charset, visited):
    if mimetype not in self.ACCEPT_TYPE: return
    handler = HTMLLinkFinder(self, url, self.reftxtdb)
    parser = HTMLParser3(handler, charset=charset)
    body = fp.read()
    parser.feed_byte(body)
    parser.close()
    if self.consumer and not visited:
      url = urljoin(handler.base_href, url)
      if url.startswith('http://'):
        name = self.baseid+url[6:]
        self.consumer.feed_page(name, body)
        if self.debug:
          print >>stderr, 'FEED: %r' % name
    return


# main
def main():
  import getopt
  def usage():
    print '''usage: textcrawler.py -o outfile [-d] [-b baseid] [-a accept_pat] [-j reject_pat]
    [-i index_html] [-m level] [-k cookie_file] [-c default_charset]
    [-U urldb] [-D delay] [-T timeout] [-L linkinfo] [url ...]'''
    sys.exit(2)
  try:
    (opts, args) = getopt.getopt(sys.argv[1:], 'db:a:j:i:m:k:c:C:U:o:D:T:L:')
  except getopt.GetoptError:
    usage()
  (debug, maxlevel, cookie_file, delay) = (0, 1, None, 0)
  (index_html, default_charset, urldb, timeout) = ('', 'iso-8859-1', None, 300)
  (baseid, outfile, linkinfo) = (None, None, 'linkinfo')
  reftxtdb = None
  acldb = None
  for (k, v) in opts:
    if k == '-d': debug += 1
    elif k == '-b': baseid = v
    elif k == '-a':
      if not acldb: acldb = ACLDB()
      acldb.add_allow(v)
    elif k == '-j':
      if not acldb: acldb = ACLDB()
      acldb.add_deny(v)
    elif k == '-m': maxlevel = int(v)
    elif k == '-i': index_html = v
    elif k == '-k': cookie_file = v
    elif k == '-c': default_charset = v
    elif k == '-U': urldb = URLDB(v)
    elif k == '-D': delay = int(v)
    elif k == '-o': outfile = v
    elif k == '-T': timeout = int(v)
    elif k == '-L': linkinfo = v
  if not args:
    usage()
  if not baseid:
    baseid = time.strftime('%Y%m%d%H%M')
  if not acldb:
    acldb = ACLDB()
    acldb.add_deny(r'\.(jpg|jpeg|gif|png|tiff|swf|mov|wmv|wma|ram|rm|rpm|gz|zip|class)\b')
    for starturl in args:
      acldb.add_allow('^'+re.escape(urljoin(starturl, '.')))
  if linkinfo:
    reftxtdb = RefTextDB(baseid)
  dumper = None
  if outfile:
    dumper = ZipDumper(outfile, baseid)
  else:
    dumper = NullDumper()               # crawling only
  for starturl in args:
    try:
      TextCrawler(dumper, starturl, baseid, reftxtdb=reftxtdb,
                  index_html=index_html, maxlevel=maxlevel,
                  cookie_file=cookie_file, default_charset=default_charset,
                  acldb=acldb, urldb=urldb, delay=delay, timeout=timeout,
                  debug=debug).run()
    except CrawlerFatalError:
      pass
  if linkinfo:
    dumper.feed_page(linkinfo, reftxtdb.dump())
  dumper.close()
  return

if __name__ == '__main__': main()
