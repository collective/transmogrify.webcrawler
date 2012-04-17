from zope.interface import classProvides, implements
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import Matcher
from collective.transmogrifier.utils import defaultKeys
import logging
import os
import sys
import urllib
import urlparse
from sys import stderr
import ConfigParser
import mimetypes, mimetools, email.utils
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from transmogrify.webcrawler.external.webchecker import MyStringIO

_marker = object()

class StaticCreatorSection(object):
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.context = transmogrifier.context

        if 'path-key' in options:
            pathkeys = options['path-key'].splitlines()
        else:
            pathkeys = defaultKeys(options['blueprint'], name, 'path')
        self.pathkey = Matcher(*pathkeys)

        self.output = options.get('output')
        self.logger = logging.getLogger('funnelweb')


    def __iter__(self):
        base = urllib.url2pathname(self.output)
        for item in self.previous:
            pathkey = self.pathkey(*item.keys())[0]

            if not pathkey or not self.output:         # not enough info
                yield item;
                continue

            path = item[pathkey]
            type = item.get('_type')
            path = os.path.join(base, urllib.url2pathname(path))
            #TODO replace field in item with file object and make other
            # blueprints expect a file. This will reduce memory usage.
            meta_data = item.get('_content_info')
            if meta_data:
                meta_data = dict(meta_data)
            if type in ['Document']:
                item['text'] = self.savefile(item['text'], path, meta_data)
            elif type in ['Page']:
                item['body'] = self.savefile(item['body'], path, meta_data)
            elif type in ['File']:
                item['file'] = self.savefile(item['file'], path, meta_data)
            elif type in ['Image']:
                item['image'] = self.savefile(item['image'], path, meta_data)
            elif type in ['Folder', 'ContentFolder']:
                makedirs(path)
            elif item.get('_html', None) is not None:
                item['_html'] = self.savefile(item['_html'], path, meta_data)
            elif item.get('_content') is not None:
                item['_content'] = self.savefile(item['_content'], path, meta_data)
            yield item


    def savefile(self, text, path, metadata):
        path = self.savefilename(path)
        if type(text) == type(u''):
            text = text.encode('utf8')
        dir, base = os.path.split(path)
        if text is None:
            self.logger.debug("None in contents %s", str(path))
            return

        makedirs(dir)
        if os.path.isdir(path):
            path = path + "index.html"

        if getattr(text, 'read', _marker) is not _marker:
            # it's a file

            # we might have already read this from the cache
            fp = text
            while getattr(fp, 'fp', None):
                fp = fp.fp
            if getattr(fp, 'name', _marker) != path:
                try:
                    with open(path, "wb") as cachefile:
                        content = fp.read()
                        cachefile.write(content)
                        cachefile.close()
                    fp.close()
                    res = OpenOnRead(path)
                except IOError, msg:
                    self.logger.error("copying file to cache %s"%path)
            else:
                res = text
        else:
            try:
                f = open(path, "wb")
                f.write(text)
            except:
                self.logger.error("writing text to cache %s"%path)
            finally:
                f.close()
            res = text
        if metadata is not None:
            mfile = ConfigParser.RawConfigParser()
            mfile.add_section('metadata')
            for key, value in metadata.items():
                mfile.set('metadata', key, value)
            with open(path + '.metadata', 'wb') as configfile:
                mfile.write(configfile)
                configfile.close()

        return res

    def savefilename(self, path):
        #type, rest = urllib.splittype(url)
        #host, path = urllib.splithost(rest)
        #path = path.lstrip("/")
        #user, host = urllib.splituser(host)
        #host, port = urllib.splitnport(host)
        #host = host.lower()
        if not path or path[-1] == "/":
            path = path + "index.html"
        if os.sep != "/":
            path = os.sep.join(path.split("/"))
            if os.name == "mac":
                path = os.sep + path
        path = os.path.join(path)
        return path


def makedirs(dir):
    if not dir:
        return
    if os.path.exists(dir):
        if not os.path.isdir(dir):
            try:
                os.rename(dir, dir + ".bak")
                os.mkdir(dir)
                os.rename(dir + ".bak", os.path.join(dir, "index.html"))
            except os.error:
                pass
        return
    head, tail = os.path.split(dir)
    if not tail:
        print "Huh?  Don't know how to make dir", dir
        return
    makedirs(head)
    os.mkdir(dir, 0777)

class OpenOnRead():
    """ File like object which only opens the file if it's read """

    def __init__(self, name, mode="r"):
        self.name = name
        self.mode = mode
        self.fp = None

    def getFile(self):
        if self.fp is None:
            self.fp = open(self.name, self.mode)
        return self.fp

    def read(self, size=-1):
        return self.getFile().read(size)

    def readline(self, size=-1):
        return self.getFile().readline(size)

    def write(self, str):
        return self.getFile().read(str)

    def close(self, size=None):
        self.getFile().close()
        self.fp = None

    def seek(self, pos):
        if pos == 0:
            #let them reopen the file on read
            self.close()
        else:
            self.getFile().seek(pos)

#TODO: replace cache code that uses hashes, e.g. http://stackoverflow.com/questions/148853/caching-in-urllib2
class CachingURLopener(urllib.FancyURLopener):

    http_error_default = urllib.URLopener.http_error_default

    def __init__(*args, **vargs):
        self = args[0]
        self.cache = vargs.get('cache',None)
        self.site_url = vargs.get('site_url',None)
        apply(urllib.FancyURLopener.__init__, args)
        self.addheaders = [
            ('User-agent', 'Transmogrifier-crawler/0.1'),
            ]

    def open(self, url, data=None):
        cache = self.cache
        old_url = url
        if cache and not url.startswith('file://'):
            cache = cache.rstrip('/')+'/'
            url = cache + url[len(self.site_url):]
            #if not url.startswith('file:'):
            #    url = 'file:'+ url
            try:
                f = self.open_local_file(url)
            except (IOError), msg:
                return urllib.FancyURLopener.open(self, old_url, data)

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
        else:
            return urllib.FancyURLopener.open(self, old_url, data)


    def http_error_401(self, url, fp, errcode, errmsg, headers):
        return None

    def open_local_file(self, url):
        """ Override base urlopener method in order to read our custom metadata
        """
        #scheme,netloc,path,parameters,query,fragment = urlparse.urlparse(url)
        host, file = urllib.splithost(url)
        localname = urllib.url2pathname(file)
        path = localname
        if os.path.isdir(path):
            if path[-1] != os.sep:
                url += '/'
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

        # add any saved metadata
        mfile = ConfigParser.ConfigParser()
        mfile.read(path+'.metadata')
        if mfile.has_section('metadata'):
            headers = dict(mfile.items('metadata'))
        else:
            try:
                stats = os.stat(localname)
            except OSError, e:
                raise IOError(e.errno, e.strerror, e.filename)
            size = stats.st_size
            modified = email.utils.formatdate(stats.st_mtime, usegmt=True)
            mtype = mimetypes.guess_type(url)[0]
            headers = mimetools.Message(StringIO(
                'Content-Type: %s\nContent-Length: %d\nLast-modified: %s\n' %
                (mtype or 'text/plain', size, modified)))
        if not host:
            urlfile = file
            if file[:1] == '/':
                urlfile = 'file://' + file
            return urllib.addinfourl(OpenOnRead(localname, 'rb'),
                              headers, urlfile)
        host, port = urllib.splitport(host)
        if not port \
           and socket.gethostbyname(host) in (urllib.localhost(), urllib.thishost()):
            urlfile = file
            if file[:1] == '/':
                urlfile = 'file://' + file
            return urllib.addinfourl(OpenOnRead(localname, 'rb'),
                              headers, urlfile)
        raise IOError, ('local file error', 'not on local host')

