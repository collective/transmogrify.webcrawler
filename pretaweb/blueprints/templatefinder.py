
import fnmatch
from zope.interface import classProvides
from zope.interface import implements
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import Matcher

from webstemmer.analyze import PageFeeder, LayoutAnalyzer
from webstemmer.zipdb import ACLDB
from lxml import etree
import lxml.html
import lxml.html.soupparser

from StringIO import StringIO


"""
XPath Tests
===========

We want to take webstemmers patterns and get the actually html rather than just
the text. To do this we will convert a pattern to xpath

    >>> pat = 'div:class=section1/p:align=center:class=msonormal/span'
    >>> xp = toXPath(pat)
    '//div[re:test(@class,"^section1$","i")]/p[re:test(@align,"^center$","i")][re:test(@class,"^msonormal$","i")]/span'

Lets check it gets the right parts of the text

    >>> text = '<div class="Section1">\n\n<p class="MsoNormal" align="center" style="text-align:center"><b style="mso-bidi-font-weight:
 normal"><span lang="EN-AU" style="font-size:20.0pt"/></b></p>\n\n<p class="MsoNormal" align="center" style="text-align:
center"><b style="mso-bidi-font-weight: normal"><span lang="EN-AU" style="font-size:20.0pt">Customer Service Standards</
span></b></p>\n\n<p class="MsoNormal"><span lang="EN-AU"/></p>\n\n<p class="MsoNormal"><span lang="EN-AU"/></p>\n\n<p cl
ass="MsoNormal"><span lang="EN-AU"/></p>\n\n<p class="MsoNormal" style="margin-top:0cm;margin-right:-23.55pt;margin-bott
om: 0cm;margin-left:45.1pt;margin-bottom:.0001pt;text-indent:-27.0pt;mso-pagination: none;mso-list:l2 level1 lfo3;tab-st
ops:list 45.0pt"><b style="mso-bidi-font-weight:normal"><span lang="EN-AU" style="font-size:16.0pt; mso-fareast-font-fam
ily:Arial"><span style="mso-list:Ignore">1.<span style="font:7.0pt "/>Times New Roman""&gt;\n</span></span></b></p><b st
yle="mso-bidi-font-weight:normal"><span lang="EN-AU" style="font-size:16.0pt">Care for the customer and show respect for
\nthem and their property.</span></b></div>'

    >>> parser = etree.XMLParser(recover=True)
    >>> tree = etree.parse(StringIO(text), parser)
    >>> nodes = tree.xpath(xp,namespaces=ns)
    >>> result = etree.tostring(nodes[0])


"""


ns = {'re':"http://exslt.org/regular-expressions"}

import re
attr = re.compile(r':(?P<attr>[^/:]*)=(?P<val>[^/:]*)')
def toXPath(pat):
    #td:valign=top/p:class=msonormal/span
    pat = attr.sub(r'[re:test(@\g<attr>,"^\g<val>$","i")]', pat)
    pat = pat.replace('/','//')
    return "//"+pat



class TemplateFinder(object):
    classProvides(ISectionBlueprint)
    implements(ISection)



    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.auto=options.get('auto',True)
        self.groups = {}
        for key,value in options.items():
            try:
                group,field = key.split('_',1)
            except:
                continue
            group = self.groups.setdefault(group,{})
            group[field] = value.strip().split('\n')
            

    def __iter__(self):
        
        if self.auto:
            items = self.analyse(self.previous)
        else:
            items = self.previous
                    
        for item in items:
            path,content = self.ishtml(item)
            if not path:
                yield item
                continue
            tree = lxml.html.soupparser.fromstring(item['text'])
            auto = self.groups.get(path,{})
            groups = self.groups.values() + [auto]
            for group in groups:
                if group.get('path',path) != path:
                    continue
                title,text = self.extract(group.items(),tree)
                if title or text:
                    if text:
                        item['text'] = text
                    if title:
                        item['title'] = ' '.join(title.split())
                    item['_template'] = True #TODO: make it the real template
                    break
            yield item


    def extract(self, pats, tree):
        res = ''
        title = ''
        for field,xps in pats:
            for xp in xps:
                result = tree.xpath(xp,namespaces=ns)
                if not result:
                    return '',''
                for node in result:
                    if field == 'title':
                        title += etree.tostring(node,method='text',encoding='utf8')+' '
                    else:
                        res += etree.tostring(node,method='html')
                if result:
                    #TODO create a template without content
                    pass
        return title,res

    def ishtml(self, item):
              path = item.get('_path',None)
              content = item.get('_content',None) or item.get('text',None)
              mimetype = item.get('_mimetype',None)
              if  path and content and mimetype in ['text/xhtml', 'text/html']:
                  return path,content
              else:
                  return None,None
        

    def analyse(self, previous):

          (debug, cluster_threshold, title_threshold, score_threshold, default_charset) = (0, 0.97, 0.6, 100, 'utf-8')
          mangle_pat = None
          linkinfo = 'linkinfo'
          #
          analyzer = LayoutAnalyzer(debug=debug)
          if mangle_pat:
            analyzer.set_encoder(mangle_pat)

          feeder = PageFeeder(analyzer, linkinfo=linkinfo, acldb=None,
                                default_charset=default_charset, debug=debug)
          
          items = []
          for item in previous:
              path,content = self.ishtml(item)
              if path:
                  feeder.feed_page(path, content)
                  items.append(item)
              else:
                  yield item
          feeder.close()
          
          cluster = {}
          for c in analyzer.analyze(cluster_threshold, title_threshold):
            if c.pattern and score_threshold <= c.score:
                for p in c.pages:
                    cluster[p.name] = c

          for item in items:
              path = item.get('_path')
              c = cluster.get(path)
              if path and c:
                  #parser = etree.HTMLParser(recover=True)
                  #tree = etree.parse(StringIO(item['text']), parser)
                  tree = lxml.html.soupparser.fromstring(item['text'])
                  failed = False
                  group = {'text':[],'title':[],'path':path}
                  index = 0
                  for diffscore, diffscorewight, pat in c.pattern:
                      #TODO: need to make this section work
                      if not pat:
                          continue
                      xp = toXPath(pat)
                      print path,pat,xp,c.title_sectno==index
                      if c.title_sectno == index:
                          group['title'].append(xp)
                      else:
                          group['text'].append(xp)
                      index = index +1
                  self.groups[path] = group
              yield item
                          
       
 
    
