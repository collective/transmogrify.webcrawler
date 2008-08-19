
from zope.interface import implements
from zope.interface import classProvides

from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection

from pretaweb.blueprints.external.webchecker import Checker
from pretaweb.blueprints.external.webchecker import MyURLopener


class WebCrawler(object):
    classProvides(ISectionBlueprint)
    implements(ISection)
    
    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.open_url = MyURLopener().open
        
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

        checker = Checker()
        checker.setflags(checkext   = self.checkext, 
                         verbose    = self.verbose,
                         maxpage    = self.maxpage, 
                         roundsize  = self.roundsize,
                         nonames    = self.nonames)
        checker.addroot(self.site_url)
        checker.run()

        # pass preccesed files
        for file in checker.done:
            if file[0].startswith(self.site_url):
                file_path = file[0][len(self.site_url):]
                if file_path:
                    # TODO :: we should subclass webchecker so it read files only once
                    try:
                        content = self.open_url(self.site_url+file_path)
                        yield dict(_path         = file_path,
                                   _site_url     = self.site_url,
                                   _content      = content.read(),
                                   _content_info = content.info(),)
                    except:
                        yield dict(_bad_url = self.site_url+file_path)
                        continue
                    self.close_handler(content)

                    
            else:
                yield dict(_bad_url = file[0])
        
        # there are also bad links (files)
        for file in checker.bad:
            yield dict(_bad_url = file[0], info=file)

    def close_handler(self, f):
        try:
            url = f.geturl()
        except AttributeError:
            pass
        else:
            if url[:4] == 'ftp:' or url[:7] == 'file://':
                # Apparently ftp connections don't like to be closed
                # prematurely...
                text = f.read()
        f.close()
