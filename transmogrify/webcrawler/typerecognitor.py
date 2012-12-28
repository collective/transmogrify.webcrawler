
import os
import cgi
import mimetypes
import urllib

from zope.interface import implements
from zope.interface import classProvides

from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection

import logging

"""
transmogrify.webcrawler.typerecognitor
======================================

A blueprint for assigning content type based on the mime-type as given by the
webcrawler
"""


class TypeRecognitor(object):
    classProvides(ISectionBlueprint)
    implements(ISection)

    types_map = {
        # mimetype                        # plone type  # tranform
        'text/plain':                     ('File',  None),
        'text/xhtml':                     ('Document',  None),
        'text/html':                      ('Document',  None),
        'application/msword':             ('File',  'doc_to_html'),
        'application/vnd.ms-word':        ('File',  'doc_to_html'),
        'application/pdf':                ('File',  'pdf_to_html'),
        'application/x-pdf':              ('File',  'pdf_to_html'),
        'application/vnd.ms-excel':       ('File',  'excel_to_html'),
        'application/msexcel':            ('File',  'excel_to_html'),
        'application/vnd.ms-powerpoint':  ('File',  'ppt_to_html'),
        'image/bmp':                      ('Image',     None),
        'image/jpeg2000':                 ('Image',     None),
        'image/png':                      ('Image',     None),
        'image/svg+xml':                  ('Image',     None),
        'image/tiff':                     ('Image',     None),
        'image/jpeg':                     ('Image',     None),
        'image/gif':                      ('Image',     None),
        }
    

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.logger = logging.getLogger(name)

    def __iter__(self):
        recognized = {}
        for item in self.previous:
            # dont except bad links 
            if '_bad_url' in item:
                yield item; continue

            # if type is defined then dont mess with it
            if '_type' in item:
                yield item; continue

            if '_redir' in item:
                # it's a redirection
                item['_type'] = 'Link'
                item['remoteUrl'] = relative_url(item['_path'], item['_redir'])
                recognized.setdefault( (item['_type'],''), []).append(item)
                yield item; continue

            # needed parameters to be able to recognize
            if '_path' not in item or \
               '_content' not in item:
                yield item; continue
            

            item.update(self.getFileType(item.get('_content_info'), item['_path']))
            recognized.setdefault( (item['_type'],item['_mimetype']), []).append(item)
            self.logger.debug('"%(_path)s" is "%(_type)s" from mimetype %(_mimetype)s"' % item)

            # copy content to appropriate field
            if item['_type'] == 'File':
                item['file'] = item['_content']
                item['file.filename'] = item['_path'].split('/')[-1]
                item['file.mimetype'] = item['_mimetype']
            elif item['_type'] == 'Image':
                item['image'] = item['_content']
                item['image.filename'] = item['_path'].split('/')[-1]
                item['image.mimetype'] = item['_mimetype']
            elif item['_type'] == 'Document':
                item['text'] = item['_content']
            del item['_content']
            if '_html' in item:
                del item['_html']
            
            yield item

        #give some helpful summary
        for key,value in sorted(recognized.items()):
            _type, mime = key
            self.logger.info("%s, %s: %d" % (_type,mime, len(value)))



    def getFileType(self, info, path):
        # recognize type of data
            
        if info is None or info.has_key('content-type'):
            ctype = cgi.parse_header(info['content-type'])[0].lower()
            if ';' in ctype:
                # handle content-type: text/html; charset=iso8859-1 :
                ctype = ctype.split(';', 1)[0].strip()
        else:
            ctype, encoding = mimetypes.guess_type(path)

        if ctype in self.types_map:
            transform = self.types_map[ctype][1],
            if transform:
                return dict(_type      = self.types_map[ctype][0],
                            _mimetype  = ctype)
            else:
                return dict(_type      = self.types_map[ctype][0],
                            _mimetype  = ctype)

        return dict(_type      = 'File',
                    _mimetype  = ctype)


#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
#
# Create a relative URL given to absolute URLs
# See tests at the end:
# test_relative_url("http://foo/a/b", "http://foo/c", "../c")
#
# (c) May 2002 Thomas Guettler http://www.thomas-guettler.de
# This code is in the public domain
# Feedback Welcome
#

import urlparse
import re
import string


def relative_url(source, target):
    su=urlparse.urlparse(source)
    tu=urlparse.urlparse(target)
    junk=tu[3:]
    if su[0]!=tu[0] or su[1]!=tu[1]:
        #scheme (http) or netloc (www.heise.de) are different
        #return absolut path of target
        return target
    su=re.split("/", su[2])
    tu=re.split("/", tu[2])
    su.reverse()
    tu.reverse()

    #remove parts which are equal   (['a', 'b'] ['a', 'c'] --> ['c'])
    while len(su)>0 and len(tu)>0 and su[-1]==tu[-1]:
        su.pop()
        last_pop=tu.pop()
    if len(su)==0 and len(tu)==0:
        #Special case: link to itself (http://foo/a http://foo/a -> a)
        tu.append(last_pop)
    if len(su)==1 and su[0]=="" and len(tu)==0:
        #Special case: (http://foo/a/ http://foo/a -> ../a)
        su.append(last_pop)
        tu.append(last_pop)
    tu.reverse()
    relative_url=[]
    for i in range(len(su)-1):
        relative_url.append("..")
    rel_url=string.join(relative_url + tu, "/")
    rel_url=urlparse.urlunparse(["", "", rel_url, junk[0], junk[1], junk[2]])
    return rel_url
