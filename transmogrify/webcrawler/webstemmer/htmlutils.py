#!/usr/bin/env python
#
# htmlutils.py
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

import re, codecs


##  Define extra Codecs
##

# mappings from html charsets to python codecs.
ALT_CODECS = {
  'euc': 'euc-jp',
  'x-euc-jp': 'euc-jp',
  'x-sjis': 'ms932',
  'x-sjis-jp': 'ms932',
  'shift-jis': 'ms932',
  'shift_jis': 'ms932',
  'sjis': 'ms932',
  'gb2312': 'gbk',
  'gb2312-80': 'gbk',
  'gb-2312': 'gbk',
  'gb_2312': 'gbk',
  'gb_2312-80': 'gbk',
}
ASCII_ENCODER = codecs.getencoder('ascii')
def getencoder(name): return codecs.getencoder(ALT_CODECS.get(name, name))
def getdecoder(name): return codecs.getdecoder(ALT_CODECS.get(name, name))


# Remove extra blanks.
RMSP_PAT = re.compile(ur'\s+')
def rmsp(s):
  return RMSP_PAT.sub(u' ', s.strip())

# Concatenate all strings with removing extra blanks.
def concat(r):
  return rmsp(u''.join(r)).strip()

# quotestr(s, codec)
def quotestr(s, quote_special=True):
  if quote_special:
    s = s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')
  return ASCII_ENCODER(s, 'xmlcharrefreplace')[0]

# attr2str
def attr2str(attrseq):
  s = ''
  for (k,v) in attrseq:
    if k.startswith('_'): continue
    s += ' '
    if v == None:
      s += quotestr(k)
    else:
      s += '%s="%s"' % (quotestr(k), quotestr(v))
  return s

    
##  HTML tags
##

BLOCK_TAGS = set(
  "title p h1 h2 h3 h4 h5 h6 tr td th dt dd li "
  "ul ol dir menu pre dl div center frameset "
  "blockquote table fieldset address".split(" "))

CDATA_TAGS = set(
  'script style'.split(' '))

INLINE_TAGS = set(
  'comment tt i b u s strike big small nobr em strong dfn code samp kbd var cite abbr '
  'acronym a applet object button font map q sub sup span bdo layer ilayer iframe '
  'select textarea label button option'.split(' '))

INLINE_IMMED_TAGS = set(
  'basefont br area link img param hr input '
  'colgroup col frame isindex meta base embed'.split(' '))

NON_NESTED_TAGS = set(
  'html head body noembed noframes noscript nolayer'.split(' '))

FORM_FIELD_TAGS = set(
  'input select textarea fieldset label'.split(' '))

NON_DISPLAYED_TAGS = set(
  'style script comment option'.split(' '))

BREAK_LINE_TAGS = BLOCK_TAGS.copy()
BREAK_LINE_TAGS.add('br')

VALID_TAGS = set()
for d in (BLOCK_TAGS, CDATA_TAGS, INLINE_TAGS, INLINE_IMMED_TAGS, NON_NESTED_TAGS):
  VALID_TAGS.update(d)
