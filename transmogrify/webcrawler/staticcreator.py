#from zope import event
from zope.interface import classProvides, implements
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import Matcher
from collective.transmogrifier.utils import defaultKeys
import logging
logger = logging.getLogger('funnelweb')
import os
import sys
import urllib
from sys import stderr


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

    
    def __iter__(self):
        base =urllib.url2pathname(self.output)
        for item in self.previous:
            
            pathkey = self.pathkey(*item.keys())[0]
            
            if not pathkey or not self.output:         # not enough info
                yield item; continue
            
            path = item[pathkey]
            type = item.get('_type')
            path = os.path.join(base,urllib.url2pathname(path))
            if type in ['Document']:
                self.savefile(item['text'],path)
            elif type in ['Page']:
                self.savefile(item['body'],path)
            elif type in ['File']:
                self.savefile(item['file'],path)
            elif type in ['Image']:
                self.savefile(item['image'],path)
            elif type in ['Folder','ContentFolder']:
                makedirs(path)
            elif item.get('_content') is not None:
                self.savefile(item['_content'], path)
            yield item


    def savefile(self, text, path):
        path = self.savefilename(path)
        if type(text) == type(u''):
            text = text.encode('utf8')
        dir, base = os.path.split(path)
        if text is None:
            msg = "static creator: None in contents %s" %str(path)
            logger.log(logging.DEBUG, msg)
            print >> stderr, msg
            return
        
            
        makedirs(dir)
        if os.path.isdir(path):
            path = path + "index.html"            
        try:
            f = open(path, "wb")
            f.write(text)
            f.close()
        except IOError, msg:
            pass

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
