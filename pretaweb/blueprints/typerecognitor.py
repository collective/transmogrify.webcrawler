
import os
import cgi
import mimetypes
import urllib

from zope.interface import implements
from zope.interface import classProvides

from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection

from pretaweb.blueprints.external.webchecker import MyURLopener
from pretaweb.blueprints.external.webchecker import MyStringIO



class TypeRecognitor(object):
    classProvides(ISectionBlueprint)
    implements(ISection)

    types_map = {
        # mimetype                        # plone type  # tranform
        'text/plain':                     ('Document',  None),
        'text/xhtml':                     ('Document',  None),
        'text/html':                      ('Document',  None),
        'application/msword':             ('Document',  'doc_to_html'),
        'application/vnd.ms-word':        ('Document',  'doc_to_html'), 
        'application/pdf':                ('Document',  'pdf_to_html'), 
        'application/x-pdf':              ('Document',  'pdf_to_html'),
        'application/vnd.ms-excel':       ('Document',  'excel_to_html'), 
        'application/msexcel':            ('Document',  'excel_to_html'),
        'application/vnd.ms-powerpoint':  ('Document',  'ppt_to_html'),
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

        # TODO :: some way of updating self.types_map
    
    def __iter__(self):
        for item in self.previous:
            
            # needed parameters to be able to recognize
            if '_path' not in item or '_site_url' not in item:
                continue
            
            url = item['_site_url'] + item['_path'] 
            
            f = MyURLopener().open(url)
            if f:
                item.update(self.getFileType(f.info(), url))
            
            yield item
        
    def getFileType(self, info, file):
        # recognize type of data
        if info.has_key('content-type'):
            ctype = cgi.parse_header(info['content-type'])[0].lower()
            if ';' in ctype:
                # handle content-type: text/html; charset=iso8859-1 :
                ctype = ctype.split(';', 1)[0].strip()
        else:
            ctype, encoding = mimetypes.guess_type(url)

        # is file a folder
        #isFolder = False
        #for item in file_list:
        #    if file is not item['_path'] and \
        #       item['_path'][len(file):len(file)+1] is '/' and \
        #       item['_path'].startswith(file):
        #        isFolder = True
        #        break
        #if isFolder:
        #    return dict(_type      = 'Folder', 
        #                _transform = None, 
        #                _mimetype  = None)

        if ctype in self.types_map:
            return dict(_type      = self.types_map[ctype][0], 
                        _transform = self.types_map[ctype][1], 
                        _mimetype  = ctype)
        return dict(_type      = 'File', 
                    _transform = None, 
                    _mimetype  = ctype)


