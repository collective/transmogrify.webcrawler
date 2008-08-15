
import fnmatch
from zope.interface import classProvides
from zope.interface import implements
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from pretaweb.blueprints.external.webchecker import Checker
from collective.transmogrifier.utils import Matcher



class WebCrawler(object):
    classProvides(ISectionBlueprint)
    implements(ISection)

    types_map = {
        '*.[Hh][Tt][Mm][Ll]': ('Document', None),
        '*.[Hh][Tt][Mm]':     ('Document', None),
        '*.[Dd][Oo][Cc]':     ('Document', 'doc_to_html'),
        }
    file_list = []
    

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        
        CHECKEXT = 1        # Check external references (1 deep)
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

        self.checker = Checker()
        self.checker.setflags(checkext   = self.checkext, 
                   verbose    = self.verbose,
                   maxpage    = self.maxpage, 
                   roundsize  = self.roundsize,
                   nonames    = self.nonames)
        self.checker.addroot(self.site_url)
        self.checker.run()

        # TODO :: what should i do with self.checkerbad
        # TODO :: should i check if self.checker.todo is empty "[]"

        # create list to sort it first 
        # this is needed so containers are created first
        # otherwise objects are not created
        for file in self.checker.done:
            file_path = file[0][len(self.site_url):]
            # TODO :: should i pass the site_url path or should i store it differently
            #         maybe is already in some index.html ... need to test how this works
            if file_path:
                self.file_list.append(file_path)
        self.file_list.sort() # sort it on the end

        for file in self.file_list:
            type, tranform = self.getFileType(file)

            text = ''
            f = self.checker.openpage((self.site_url+file, ''))
            if f:
                text = f.read()

            # workflow
            transition = 'publish'
            if type in ['Image', 'File']:
                transition = None

            yield dict(_path = file,
                       _type = type,
                       _transitions = transition,
                       _transform = tranform,
                       text = text,
                       )

    def getFileType(self, file):
      for pattern, item in self.types_map.items():
          if fnmatch.fnmatch(file, pattern):
              return item
      # check for folder
      isFolder = False
      for item in self.file_list:
          if file is not item and \
             item.startswith(file):
              isFolder = True
              break
      if isFolder:
          return 'Folder', None






