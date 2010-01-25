#!/usr/bin/env python
#
# analyze.py
#
#  Copyright (c) 2005-2006  Yusuke Shinyama <yusuke at cs dot nyu dot edu>
#
#  Permission is hereby granted, free of charge, to any person
#  obtaining a copy of this software and associated documentation
#  files (the "Software"), to deal in the Software without
#  restriction, including without limitation the rights to use,
#  copy, modify, merge, publish, distribute, sublicense, and/or
#  sell copies of the Software, and to permit persons to whom the
#  Software is furnished to do so, subject to the following
#  conditions:
#
#  The above copyright notice and this permission notice shall be
#  included in all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY
#  KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
#  WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
#  PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
#  COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
#  OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
#  SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

import sys, re
from difflib import SequenceMatcher
from htmlparser3 import HTMLParser3
from textcrawler import HTMLLinkFinder, wash_url
from htmldom import parse
from zipdb import ACLDB, ZipLoader
from urlparse import urljoin
from layoutils import sigchars, get_textblocks, retrieve_blocks, WEBSTEMMER_VERSION, KEY_ATTRS
from math import log

upperbound = min
lowerbound = max
stderr = sys.stderr


##
##  Scoring functions
##

def titlability0(s1, s2):
  # s1:title, s2:body
  m = [ [ (0,0) for _ in s2 ] for _ in s1 ]
  for p1 in xrange(len(s1)):
    for p2 in xrange(len(s2)):
      if s1[p1] == s2[p2]:
        if p1 == 0 or p2 == 0:
          (a,b) = (0,0)
        else:
          (a,b) = m[p1-1][p2-1]
        m[p1][p2] = (a,b+1)
      else:
        (a1,b1) = m[p1][p2-1]
        (a2,b2) = m[p1-1][p2]
        m[p1][p2] = (max(a1+b1*b1, a2+b2*b2), 0)
  (score, dummy) = m[-1][-1]
  return score / float(len(s1))

def seqmatch(s1, s2):
  if len(s1) < len(s2):
    return [ (b,a,n) for (a,b,n) in SequenceMatcher(None, s2, s1).get_matching_blocks() ]
  else:
    return SequenceMatcher(None, s1, s2).get_matching_blocks()

def titlability(title, body):
  return sum( n*n for (a,b,n) in seqmatch(title, body) ) / float(len(title))

def dice_coeff(s1, s2):
  return 2*sum( n for (a,b,n) in seqmatch(s1, s2) ) / float(len(s1)+len(s2))

def diff_score(s1, s2):
  return len(s1) + len(s2) - 2*sum( n for (a,b,n) in seqmatch(s1, s2) )

def find_lcs(s1, s2):
  r = []
  for (a,b,n) in seqmatch(s1, s2):
    r.extend( (a+i,b+i) for i in xrange(n) )
  return r

def gmax(seq, key=lambda x:x, default=object()):
  (m,k0) = (default, 0)
  for x in seq:
    k1 = key(x)
    if m == default or k0 < k1: (m,k0) = (x,k1)
  return m


##  LayoutSectionCluster
##
class LayoutSectionCluster:

  # blockgroups: [ blocks_doc1, blocks_doc2, ..., blocks_docn ]
  def __init__(self, id, blockgroups):
    self.id = id
    self.diffscore = None
    self.weight = sum( sum( b.weight for b in blocks ) for blocks in blockgroups )
    self.weight_noanchor = sum( sum( b.weight_noanchor for b in blocks ) for blocks in blockgroups )
    self.weight_avg = self.weight_noanchor / float(len(blockgroups))
    self.blockgroups = blockgroups
    return

  def __repr__(self):
    return '<SC-%d (diff=%s, weight_noanchor=%d): %r>' % \
           (self.id, self.diffscore, self.weight_noanchor, self.blockgroups[0][0].path)

  def calc_diffscore(self):
    (maxscore, score) = (0, 0)
    block_texts = [ ''.join( b.sig_text for b in blocks ) for blocks in self.blockgroups ]
    for (i,text0) in enumerate(block_texts):
      if not text0: continue
      for text1 in block_texts[i+1:]: # 0 <= j < i
        if not text1: continue
        maxscore += len(text0)+len(text1)
        score += diff_score(text0, text1)
    self.diffscore = score / float(lowerbound(maxscore, 1.0))
    return


##  find_clusters
##
def find_clusters(para_blocks):

  def uniq_path(blocks):
    r = []
    prev = None
    for b in blocks:
      if prev == None or b.path != prev:
        r.append(b.path)
      prev = b.path
    return r

  def find_common(seqs):
    s0 = None
    for s1 in seqs:
      if s0 == None:
        s0 = s1
      else:
        s0 = [ s0[i0] for (i0,i1) in find_lcs(s0, s1) ]
    return s0

  # obtain the common paths.
  common_paths = find_common([ uniq_path(blocks) for blocks in para_blocks ])

  # clusters = [ ( doc1_blocks1, doc2_blocks1, ..., docm_blocks1 ),
  #                ...
  #              ( doc1_blocksn, doc2_blocksn, ..., docm_blocksn ) ]
  clusters = zip(*[ retrieve_blocks(common_paths, blocks) for blocks in para_blocks ])

  # compare each cluster of text blocks.
  layout = []
  for blockgroups in clusters:
    if blockgroups[0]:
      layout.append(LayoutSectionCluster(len(layout), blockgroups))

  return layout


##  LayoutCluster
##
class LayoutCluster:

  def __init__(self, name, debug=0):
    self.name = name
    self.debug = debug
    self.pages = []
    self.score = 0
    self.pattern = None
    self.title_sectno = -1
    return

  def __repr__(self):
    return '<%s>' % self.name

  def add(self, page):
    self.pages.append(page)
    return

  def fixate(self, title_threshold):
    if len(self.pages) < 2: return
    layout = find_clusters([ p.blocks for p in self.pages ])
    if not layout: return
    # obtain the diffscores of this layout.
    for sect in layout:
      sect.calc_diffscore()
    # why log?
    self.score = log(len(self.pages)) * sum( sect.diffscore * sect.weight_avg for sect in layout )
    # discover main sections.
    self.pattern = [ (sect.diffscore, sect.diffscore*sect.weight_avg,
                      sect.blockgroups[0][0].path) for sect in layout ]
    largest = gmax(layout, key=lambda sect: sect.diffscore*sect.weight_avg)
    if self.debug:
      for sect in layout:
        print >>stderr, ' main: sect=%s, diffscore=%.2f, mainscore=%.2f, text=%s' % \
              (sect, sect.diffscore, sect.diffscore*sect.weight_avg,
               ''.join( b.sig_text for b in sect.blockgroups[0]))

    # discover title and main sections.
    if self.debug:
      print >>stderr, 'Fixating: cluster=%r, pattern=%r, largest=%r' % (self, self.pattern, largest)
    title_sect_voted = {}
    for (pageno,p) in enumerate(self.pages):
      title_sect = None
      title_score = title_threshold
      if self.debug:
        print >>stderr, '%r: anchor_strs=%r' % (p, p.anchor_strs)
      # if anchor strings are available, compare them to the section texts.
      if p.anchor_strs:
        for i in xrange(largest.id):
          sect = layout[i]
          title = ''.join( b.sig_text for b in sect.blockgroups[pageno] )
          if not title: continue
          score = max( dice_coeff(rt, title) for rt in p.anchor_strs if rt ) * sect.diffscore
          if self.debug:
            print >>stderr, ' title: sect=%s, score=%.2f, title=%r' % (sect, score, title)
          if title_score < score:
            (title_sect, title_score) = (sect, score)

      # otherwise, use a fallback method.
      if not title_sect and 1 < len(layout):
        largest_text = ''.join( b.sig_text for b in largest.blockgroups[pageno] )
        if self.debug:
          print >>stderr, 'FALLBACK:', largest_text[:50]
        title_score = 1.0
        for i in xrange(largest.id):
          sect = layout[i]
          title = ''.join( b.sig_text for b in sect.blockgroups[pageno] )
          if not title: continue
          score = titlability(title, largest_text) * sect.diffscore
          if self.debug:
            print >>stderr, ' sect=%s, score=%.2f, title=%r' % (sect, score, title)
          if title_score < score:
            (title_sect, title_score) = (sect, score)

      if title_sect not in title_sect_voted: title_sect_voted[title_sect] = 0
      title_sect_voted[title_sect] += 1
      if self.debug:
        print >>stderr, 'title_sect=%r' % title_sect

    (title_sect, dummy) = gmax(title_sect_voted.iteritems(), key=lambda (k,v): v)
    if title_sect:
      self.title_sectno = title_sect.id
    else:
      self.title_sectno = -1
    return

  def dump(self):
    print '#', self.score, self
    for p in self.pages:
      print '#\t', p.name
    print (self.score, self.name, self.title_sectno, self.pattern)
    print
    return


##  LayoutAnalyzer
##
class HTMLPage:

  def __init__(self, name, tree, encoder=None):
    self.name = name
    self.blocks = get_textblocks(tree, encoder)
    self.weight = sum( b.weight for b in self.blocks )
    #self.weight_noanchor = sum( b.weight_noanchor for b in self.blocks )
    self.anchor_strs = []
    return

  def __repr__(self):
    return '<%s>' % self.name

  def add_anchor_strs(self, anchor_strs):
    for s in anchor_strs:
      s = sigchars(s)
      if s:
        self.anchor_strs.append(s)
    return

class LayoutAnalyzer:

  def __init__(self, debug=0):
    self.pages = {}
    self.debug = debug
    self.encoder = None
    return

  def set_encoder(self, mangle_pat):
    pat = re.compile(mangle_pat)
    def encode_element2(e):
      return e.tag + ''.join(sorted( ':%s=%s' % (k.lower(), ''.join(pat.findall(e.attrs[k].lower())))
                                     for k in e.attrs.keys() if k in KEY_ATTRS ))
    self.encoder = encode_element2
    return

  def add_tree(self, name, tree):
    page = HTMLPage(name, tree, encoder=self.encoder)
    self.pages[name] = page
    return len(self.pages)

  def add_anchor_strs(self, name, anchor_strs):
    if name in self.pages:
      p = self.pages[name]
      for s in anchor_strs:
        s = sigchars(s)
        if s:
          p.anchor_strs.append(s)
    return

  def analyze(self, cluster_threshold=0.97, title_threshold=0.6, verbose=True):
    print >>stderr, 'Clustering %d files with threshold=%f...' % (len(self.pages), cluster_threshold)
    clusters = []
    keys = self.pages.keys()

    for (urlno,url1) in enumerate(keys):
      page1 = self.pages[url1]
      if self.debug:
        print >>stderr, ' %d: %r' % (urlno, page1)
      elif verbose:
        stderr.write(' %d: ' % urlno)
      # search from the smallest cluster (not sure if this helps actually...)
      clusters.sort(key=lambda c: len(c.pages))
      for c0 in clusters:
        for page2 in c0.pages:
          layout = find_clusters([ page1.blocks, page2.blocks ])
          total_weight = sum( c.weight for c in layout )
          sim = total_weight / lowerbound(float(page1.weight + page2.weight), 1)
          if self.debug:
            print >>stderr, '    sim=%.3f (%d): %r' % (sim, total_weight, page2)
          elif verbose:
            stderr.write('.'); stderr.flush()
          if sim < cluster_threshold: break
        else:
          if verbose:
            print >>stderr, 'joined: %r' % c0
          c0.add(page1)
          break
      else:
        c0 = LayoutCluster(url1, debug=self.debug)
        c0.add(page1)
        if verbose:
          print >>stderr, 'formed: %r' % c0
        clusters.append(c0)

    stderr.write('Fixating')
    for c in clusters:
      c.fixate(title_threshold)
      stderr.write('.'); stderr.flush()
    clusters.sort(key=lambda c: c.score, reverse=True)
    print >>stderr
    return clusters


##  PageFeeder
##
class PageFeeder:

  def __init__(self, analyzer, linkinfo='linkinfo', default_charset='utf-8',
               acldb=None, debug=0):
    self.analyzer = analyzer
    self.default_charset = default_charset
    self.debug = debug
    self.acldb = acldb
    self.linkinfo = linkinfo
    self.dic = {}
    self.baseid = None
    return

  # dirtie
  def accept_url(self, url):
    return url
  def inject_url(self, url):
    return True
  def add(self, name, s):
    name = self.baseid+name
    if name not in self.dic: self.dic[name] = []
    self.dic[name].append(s)
    return

  def feed_page(self, name, data):
    if name == self.linkinfo:
      print >>stderr, 'Loading: %r' % name
      for line in data.split('\n'):
        if line:
          (name,strs) = eval(line)
          self.dic[name] = strs
    else:
      try:
        n = name.index('/')
      except ValueError:
        return
      base_href = 'http://'+name[n+1:]
      if not self.linkinfo:
        self.baseid = name[:n]
        handler = HTMLLinkFinder(self, base_href, self)
        parser = HTMLParser3(handler, charset=self.default_charset)
        parser.feed_byte(data)
        parser.close()
      if not self.acldb or self.acldb.allowed(name):
        tree = parse(data, charset=self.default_charset, base_href=base_href)
        n = self.analyzer.add_tree(name, tree)
        print >>stderr, 'Added: %d: %s' % (n, name)
      else:
        print >>stderr, 'Skipped: %s' % name
    return

  def close(self):
    for (name, strs) in self.dic.iteritems():
      self.analyzer.add_anchor_strs(name, strs)
    return


# main
def main():
  import getopt
  def usage():
    print '''usage: analyze.py [-d] [-t cluster_threshold] [-T title_threshold] [-S score_threshold] [-L linkinfo] [-c default_charset] [-a accept_pat] [-j reject_pat] [-P mangle_pat] files ...'''
    sys.exit(2)
  try:
    (opts, args) = getopt.getopt(sys.argv[1:], 'dt:T:S:L:c:a:j:P:')
  except getopt.GetoptError:
    usage()
  (debug, cluster_threshold, title_threshold, score_threshold, default_charset) = (0, 0.97, 0.6, 100, 'utf-8')
  acldb = None
  mangle_pat = None
  linkinfo = 'linkinfo'
  for (k, v) in opts:
    if k == '-d': debug += 1
    elif k == '-t': cluster_threshold = float(v)
    elif k == '-T': title_threshold = float(v)
    elif k == '-S': score_threshold = float(v)
    elif k == '-L': linkinfo = ''
    elif k == '-c': default_charset = v
    elif k == '-a':
      if not acldb: acldb = ACLDB()
      acldb.add_allow(v)
    elif k == '-j':
      if not acldb: acldb = ACLDB()
      acldb.add_deny(v)
    elif k == '-P':
      mangle_pat = v
  if not args:
    usage()
  #
  analyzer = LayoutAnalyzer(debug=debug)
  if mangle_pat:
    analyzer.set_encoder(mangle_pat)
  print '### version=%s' % WEBSTEMMER_VERSION
  for fname in args:
    print '### fname=%r' % fname
    feeder = PageFeeder(analyzer, linkinfo=linkinfo, acldb=acldb,
                        default_charset=default_charset, debug=debug)
    if fname.endswith('.zip'):
      ZipLoader(feeder, fname, debug=debug).run()
    elif fname.endswith('.list') or fname == '-':
      if fname == '-':
        fp = sys.stdin
      else:
        fp = file(fname)
      for line in fp:
        name = line.strip()
        if debug:
          print >>stderr, 'Loading: %r' % name
        fp2 = file(name)
        data = fp2.read()
        fp2.close()
        feeder.feed_page(name, data)
      fp.close()
    else:
      fp = file(fname)
      data = fp.read()
      fp.close()
      feeder.feed_page(fname, data)
    feeder.close()
  print '### cluster_threshold=%f' % cluster_threshold
  print '### title_threshold=%f' % title_threshold
  print '### pages=%d' % len(analyzer.pages)
  print
  if mangle_pat:
    print '!mangle_pat=%r' % mangle_pat
    print
  for c in analyzer.analyze(cluster_threshold, title_threshold):
    if c.pattern and score_threshold <= c.score:
      c.dump()
  return


# do not use psyco. it gets so large and no speedup.
#import psyco; psyco.full()
if __name__ == '__main__': main()
