
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
          
          import pdb; pdb.set_trace()
          items = []
          for item in self.previous:
              if item.get('_path',None) and item.get('_content',None):
                  feeder.feed_page(item['_path'], item['_content'])
                  items.append(item)
          feeder.close()
          
          cluster = {}
          for c in analyzer.analyze(cluster_threshold, title_threshold):
            if c.pattern and score_threshold <= c.score:
                for p in pages:
                    cluster[p] = c
                    
          for item in items:
              c = cluster.get(item['_path'])
              if c:
                  for diffscore, diffscorewight, path in c.pattern:
                      xp = toxpath(path)
                      item['title'] = transform(item[text], xp)
              yield item


