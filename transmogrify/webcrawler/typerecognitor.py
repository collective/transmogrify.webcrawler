
import os
import cgi
import mimetypes
import urllib

from zope.interface import implements
from zope.interface import classProvides

from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection

from transmogrify.webcrawler.external.webchecker import MyURLopener


class TypeRecognitor(object):
    classProvides(ISectionBlueprint)
    implements(ISection)

    types_map = {
        # mimetype                        # plone type  # tranform
        'text/plain':                     ('Document',  None),
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
        self.open_url = MyURLopener().open
    
    def __iter__(self):
        for item in self.previous:
            # dont except bad links 
            if '_bad_url' in item:
                yield item; continue

            # needed parameters to be able to recognize
            if '_path' not in item or \
               '_site_url' not in item or \
               '_content' not in item:
                yield item; continue
            
            # if type is defined then dont mess with it
            if '_type' in item:
                yield item; continue

            url = item['_site_url'] + item['_path']
            item.update(self.getFileType(item.get('_content_info'), url))
          
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
        
    def getFileType(self, info, file):
        # recognize type of data
            
        if info is None or info.has_key('content-type'):
            ctype = cgi.parse_header(info['content-type'])[0].lower()
            if ';' in ctype:
                # handle content-type: text/html; charset=iso8859-1 :
                ctype = ctype.split(';', 1)[0].strip()
        else:
            ctype, encoding = mimetypes.guess_type(url)

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

