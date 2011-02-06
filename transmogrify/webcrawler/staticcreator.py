#from zope import event
from zope.interface import classProvides, implements
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import Matcher
from collective.transmogrifier.utils import defaultKeys
import logging
import os
import sys
import urllib
from sys import stderr
import ConfigParser

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
                    f = open(path, "wb")
                    for content in text:
                        f.write(content)
                    f.close()
                    text.close()
                    res = open(path, "r")
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
