
import fnmatch
from zope.interface import classProvides
from zope.interface import implements
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import Matcher

from webstemmer.analyze import PageFeeder, LayoutAnalyzer
from webstemmer.zipdb import ACLDB

class TemplateFinder(object):
    classProvides(ISectionBlueprint)
    implements(ISection)



    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous

    def __iter__(self):

          (debug, cluster_threshold, title_threshold, score_threshold, default_charset) = (0, 0.97, 0.6, 100, 'utf-8')
          acldb = None
          mangle_pat = None
          linkinfo = 'linkinfo'
          acldb = ACLDB()
          #acldb.add_allow(v)
          #acldb.add_deny(v)
          #
          analyzer = LayoutAnalyzer(debug=debug)
          if mangle_pat:
            analyzer.set_encoder(mangle_pat)

          feeder = PageFeeder(analyzer, linkinfo=linkinfo, acldb=acldb,
                                default_charset=default_charset, debug=debug)
          
          items = []
          import pdb; pdb.set_trace()
          for item in self.previous:
              path = item.get('_path',None)
              content = item.get('_content',None) or item.get('text',None)
              mimetype = item.get('_mimetype',None)
              if  path and content and mimetype in ['text/xhtml', 'text/html']:
                  feeder.feed_page(item.get('_site_url'), content)
                  items.append(item)
              else:
                  yield item
          feeder.close()
          
          cluster = {}
          for c in analyzer.analyze(cluster_threshold, title_threshold):
            if c.pattern and score_threshold <= c.score:
                for p in pages:
                    cluster[p] = c
                    
          for item in items:
              path = item.get('_path')
              c = cluster.get(path)
              if path and c:
                  for diffscore, diffscorewight, path in c.pattern:
                      #TODO: need to make this section work
                      xp = toxpath(path)
                      item['title'] = transform(item[text], xp)
                      
              yield item


