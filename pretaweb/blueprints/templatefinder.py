
import fnmatch
from zope.interface import classProvides
from zope.interface import implements
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import Matcher



class WebCrawler(object):
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

          for item in self.previous:
              feeder.feed_page(item['_path'], item['text'])
          feeder.close()
          for c in analyzer.analyze(cluster_threshold, title_threshold):
            if c.pattern and score_threshold <= c.score:
              c.dump()
          return





