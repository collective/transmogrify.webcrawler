#!/usr/bin/env python
#
# layoutils.py
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
from htmldom import tag
from htmlutils import concat

WEBSTEMMER_VERSION='0.6.1'


##
##  Common routines
##

SIG_CHARS = re.compile(r'\w+', re.UNICODE)
def sigchars(s):
  return ''.join(SIG_CHARS.findall(s)).lower()

KEY_ATTRS = dict.fromkeys('id class align valign rowspan colspan'.split(' '))
def encode_element(e):
  return e.tag + ''.join(sorted( ':%s=%s' % (k.lower(), e.attrs[k].lower())
                                 for k in e.attrs.keys() if k in KEY_ATTRS ))

class TextBlock:
  
  def __init__(self, path, text, text_noanchor):
    self.path = path
    self.orig_text = text
    self.sig_text = sigchars(text)
    self.weight = len(self.sig_text)
    self.weight_noanchor = len(sigchars(text_noanchor))
    return
  
  def __repr__(self):
    return '<Text: %s %r>' % (self.path, self.orig_text[:10])


##  Chunker
##
##       <div>abc</div> -> "abc"
##       <div>abc<div>def</div></div> -> "abc" "def"
##       <div>abc<span>def</span></span> -> "abcdef"
##       <div>abc<span>def</span></span> -> "abcdef"
##       <span>abc<div>def</div>ghi</span> -> "abc" "def" "ghi"
##
class Chunker:
  
  PATH_COMPS = 3
  MIN_CHARS = 5
  SIG_TAGS = dict.fromkeys('title p h1 h2 h3 h4 h5 h6 tr td th dt dd li ul ol dl '
                           'dir menu pre div center font span blockquote table address'.split(' '))
  IGNORE_TAGS = dict.fromkeys('comment style script option'.split(' '))
  CHOP_TAGS = dict.fromkeys('hr br'.split(' '))

  def __init__(self, encoder):
    self.texts = []
    self.blocks = []
    self.encoder = encoder
    return
  
  def add(self, e, anchor):
    self.texts.append((e, anchor))
    return

  def chop(self, path):
    if self.texts:
      self.blocks.append((path, self.texts))
      self.texts = []
    return
  
  def chunk(self, e, path, anchor):
    # string object
    t = tag(e)
    if not t:
      self.add(e, anchor)
    # tag element
    elif (t == 'img') and ('alt' in e.attrs):
      s = e.attrs['alt']
      # kludge to capture DropCaps:
      #   if this is the beginning of a text chunk
      #   and there's only one char in the alt prop,
      #   it must be a dropcap.
      if len(s) == 1 and not self.texts:
        self.add(s, anchor)
    elif t in self.IGNORE_TAGS:
      pass
    elif t in self.CHOP_TAGS:
      self.chop(path)
    elif e.children:
      if t == 'a':
        anchor = True
      if t in self.SIG_TAGS:
        self.chop(path)
        path = path + [self.encoder(e).encode('ascii','replace')]
      for c in e.children:
        self.chunk(c, path, anchor)
      if t in self.SIG_TAGS:
        self.chop(path)
    return

  def getblocks(self, e):
    # chop into blocks
    r = []
    self.chunk(e, [], False)
    for (path, texts) in self.blocks:
      b = TextBlock('/'.join(path[-self.PATH_COMPS:]), 
                    concat( t for (t, a) in texts ),
                    concat( t for (t, a) in texts if not a ))
      if self.MIN_CHARS <= len(b.sig_text):
        r.append(b)
    return r

def get_textblocks(e, encoder=None):
  return Chunker(encoder=(encoder or encode_element)).getblocks(e)


##  cluster
##
# s1:src(uniq), s2:dest
def cluster_seq(s1, s2, eq):
  if not s1 or not s2: return []
  # length table: every element is set to zero.
  m = [ [ (0,0,3) for x in s2 ] for y in s1 ]
  # we maintain three values (a,b,c) at each cell:
  #  a: score (= sum of b over different letters)
  #  b: number of continuous letters
  #  c: traverse direction. 1=down, 2=across, 3=diagonal
  for p1 in range(len(s1)):
    for p2 in range(len(s2)):
      t = []
      if p1 and p2:
        # 11: decr. p1 and p2
        (a,b,c) = m[p1-1][p2-1]
        a += b
        b = 0
        if eq(s1[p1], s2[p2]): b += 1
        t.append((a+b, (a, b, 3)))
      if p2:
        # 10: (p1,p2-1): go across
        (a,b,c) = m[p1][p2-1]
        if eq(s1[p1], s2[p2]): b += 1
        t.append((a+b, (a, b, 2)))
      if p1:
        # 01: (p1-1,p2): go down
        (a,b,c) = m[p1-1][p2]
        a += b
        b = 0
        t.append((a+b, (a, b, 1)))
      if not t:
        a = 0
        b = 0
        if eq(s1[p1], s2[p2]): b += 1
        m[p1][p2] = (a, b, 3)
      else:
        t.sort()
        m[p1][p2] = t[-1][1]
  # now we traverse the table in reverse order.
  (p1, p2) = (len(s1)-1, len(s2)-1)
  cluster = [ [] for x in s1 ]
  while 1:
    (a,b,c) = m[p1][p2]
    if c & 2:
      if eq(s1[p1], s2[p2]):
        cluster[p1].insert(0, s2[p2])
      if not p2: break
      p2 -= 1
    if c & 1 and 0 < p1: p1 -= 1
  return cluster
#print cluster_seq('abcbcbcbcb', 'abcbbcbbd', lambda x:x, lambda x,y:x==y)

def retrieve_blocks(pathseq, blocks):
  return cluster_seq(pathseq, blocks, lambda p,b: p == b.path)


# testing
def main(args):
  from htmldom import parsefile
  tree = parsefile(sys.stdin)
  for b in get_textblocks(tree):
    print repr(b.path), b.orig_text[:50].encode('euc-jp', 'replace')
  return

if __name__ == '__main__': main(sys.argv[1:])
