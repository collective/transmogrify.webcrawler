#!/usr/bin/env python
#
# extract.py
#
#  Copyright (c) 2005  Yusuke Shinyama <yusuke at cs dot nyu dot edu>
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

# todo: read special hooks from patfile

import sys, re
from htmldom import parse
from zipdb import ACLDB, ZipLoader
from layoutils import sigchars, get_textblocks, retrieve_blocks, WEBSTEMMER_VERSION, KEY_ATTRS

stderr = sys.stderr


##
##  Extracting
##

class LayoutSection:

  def __init__(self, id, diffscore, mainscore, blocks):
    self.id = id
    self.diffscore = diffscore
    self.mainscore = mainscore
    self.weight = sum( b.weight for b in blocks )
    self.blocks = blocks
    return


##  LayoutPattern
##
class LayoutPattern:

  def __init__(self, name, score, title_sectno, main_sectno, pattern):
    self.name = name
    self.score = score
    self.title_sectno = title_sectno
    self.main_sectno = main_sectno
    self.pattern = pattern
    return

  def match_blocks(self, blocks0, strict=True):
    diffs = [ d for (d,m,p) in self.pattern ]
    mains = [ m for (d,m,p) in self.pattern ]
    paths = [ p for (d,m,p) in self.pattern ]
    layout = []
    for (diffscore,mainscore,blocks1) in zip(diffs, mains, retrieve_blocks(paths, blocks0)):
      if strict and not blocks1:
        return None
      layout.append(LayoutSection(len(layout), diffscore, mainscore, blocks1))
    return layout


##  LayoutPatternSet
##
class LayoutPatternSet:

  def __init__(self, debug=0):
    self.pats = []
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

  def read(self, fp):
    for line in fp:
      line = line.strip()
      if not line or line.startswith('#'): continue
      if line.startswith('!mangle_pat='):
        self.set_encoder(eval(line[line.index('=')+1:]))
        continue
      x = eval(line)
      if len(x) == 5:
        (score, name, title_sectno, main_sectno, pattern) = x
      else:
        (score, name, title_sectno, pattern) = x
        main_sectno = -1
      self.pats.append(LayoutPattern(name, score, title_sectno, main_sectno, pattern))
    return

  def identify_layout(self, tree, pat_threshold, strict=True):
    top = (None, None)
    blocks = get_textblocks(tree, encoder=self.encoder)
    if 2 <= self.debug:
      tree.dump()
    max_weight = sum( b.weight for b in blocks ) * pat_threshold
    for pat1 in self.pats:
      layout = pat1.match_blocks(blocks, strict=strict)
      if layout:
        weight = sum( sect.weight for sect in layout )
        if max_weight < weight:
          top = (pat1, layout)
          max_weight = weight
    return top

  def dump_text(self, name, tree,
                pat_threshold, diffscore_threshold, main_threshold,
                codec_out='utf-8', strict=True):
    enc = lambda x: x.encode(codec_out, 'replace')
    (pat1, layout) = self.identify_layout(tree, pat_threshold, strict=strict)
    if not layout:
      print '!UNMATCHED: %s' % name
    else:
      print '!MATCHED: %s' % name
      print 'PATTERN: %s' % pat1.name
      if self.debug:
        for sect in layout:
          print >>stderr, 'DEBUG: SECT-%d: diffscore=%.2f' % (sect.id, sect.diffscore)
          for b in sect.blocks:
            print >>stderr, '   %s' % enc(b.orig_text)
      for sectno in xrange(len(layout)):
        sect = layout[sectno]
        if sectno == pat1.title_sectno:
          for b in sect.blocks:
            print 'TITLE: %s' % enc(b.orig_text)
        elif diffscore_threshold <= sect.diffscore:
          if pat1.title_sectno < sectno and main_threshold <= sect.mainscore:
            for b in sect.blocks:
              print 'MAIN-%d: %s' % (sect.id, enc(b.orig_text))
          else:
            for b in sect.blocks:
              print 'SUB-%d: %s' % (sect.id, enc(b.orig_text))
    print
    return


##  TextExtractor
##
class TextExtractor:

  def __init__(self, patternset, pat_threshold=0.9, diffscore_threshold=0.5, mainscore_threshold=10,
               default_charset='iso-8859-1', codec_out='utf-8', strict=True,
               linkinfo='linkinfo', debug=0):
    self.pat_threshold = pat_threshold
    self.diffscore_threshold = diffscore_threshold
    self.mainscore_threshold = mainscore_threshold
    self.default_charset = default_charset
    self.codec_out = codec_out
    self.strict = strict
    self.linkinfo = linkinfo
    self.debug = debug
    self.patternset = patternset
    return

  def feed_tree(self, name, tree):
    if name == self.linkinfo: return
    self.patternset.dump_text(name, tree,
                              self.pat_threshold, self.diffscore_threshold, self.mainscore_threshold,
                              codec_out=self.codec_out, strict=self.strict)
    return

  def feed_page(self, name, fp):
    if name == self.linkinfo: return
    self.feed_tree(name, parse(fp, charset=self.default_charset))
    return



# main
def main():
  import getopt
  def usage():
    print '''usage: extract.py [-d)ebug] [-S)trict] [-t pat_threshold] [-T diffscore_threshold] [-M mainscore_threshold] [-c default_charset] [-C codec_out] [-a accept_pat] [-j reject_pat] [-P mangle_pat] patfile zipfile ...'''
    sys.exit(2)
  try:
    (opts, args) = getopt.getopt(sys.argv[1:], 'dSt:T:M:c:C:a:j:P:')
  except getopt.GetoptError:
    usage()
  (debug, pat_threshold, diffscore_threshold, mainscore_threshold, default_charset, codec_out, strict) = \
          (0, 0.8, 0.5, 50, 'iso-8859-1', 'utf-8', False)
  acldb = None
  mangle_pat = None
  for (k, v) in opts:
    if k == '-d': debug += 1
    elif k == '-S': strict = True
    elif k == '-t': pat_threshold = float(v)
    elif k == '-T': diffscore_threshold = float(v)
    elif k == '-M': mainscore_threshold = float(v)
    elif k == '-c': default_charset = v
    elif k == '-C': codec_out = v
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
  patternset = LayoutPatternSet(debug=debug)
  fp = file(args[0])
  patternset.read(fp)
  fp.close()
  if mangle_pat:
    patternset.set_encoder(mangle_pat)
  del args[0]
  consumer = TextExtractor(patternset, pat_threshold, diffscore_threshold, mainscore_threshold,
                           default_charset=default_charset, codec_out=codec_out,
                           strict=strict, debug=debug)
  if not args:
    args = ['-']
  for fname in args:
    if fname.endswith('.zip'):
      ZipLoader(consumer, fname, acldb=acldb, debug=debug).run()
    elif fname == '-':
      consumer.feed_page('stdin', sys.stdin)
    else:
      fp = file(fname)
      consumer.feed_page(fname, fp)
      fp.close()
  return

if __name__ == '__main__': main()
