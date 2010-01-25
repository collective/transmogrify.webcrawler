#!/usr/bin/env python
#
# html2txt.py - text extractor (or HTML tag ripper)
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

# html2txt.py is a much simpler text extractor (or an HTML tag
# ripper) without using any sort of predefined pattern. It just
# removes all HTML tags from the input files. It also removes
# javascript or stylesheet contents surrounded by
# <script>...</script> or <style>...</style> tag.
#
# Usage:
#   $ ./html2txt.py [options] input_filename ... > output_text
#
# Options:
#   -C output_text_encoding
#      Specifies the encoding of output texts (page titles and main texts). The default is utf-8.
#   -c default_character_set
#      Specifies the default character set that is used when there is
#      no charset declaration (<meta> tag) in an HTML file. A different
#      character set is not automatically detected.
#
    
import sys, re
from htmlutils import rmsp, getencoder
from htmlparser3 import HTMLParser3, HTMLHandler


##  HTMLTextHandler
##
class HTMLTextHandler(HTMLHandler):

  CUTSP = re.compile(ur'([\u3000-\u9fff])\n+([\u3000-\u9fff])')
  IGNORED_TAGS = dict.fromkeys(
    'comment script style select'.split(' ')
    )
  NEWLINE_TAGS = dict.fromkeys(
    'p br div td th li blockquote pre form hr h1 h2 h3 h4 h5 h6 address'.split(' ')
    )
  
  def __init__(self, out, ignored_tags=IGNORED_TAGS, newline_tags=NEWLINE_TAGS):
    self.out = out
    self.ignored_tags = ignored_tags
    self.newline_tags = newline_tags
    self.ignore = 0
    self.text = []
    return
  
  def flush(self, newline=False):
    if self.text:
      s = rmsp(self.CUTSP.sub(r'\1\2', ''.join(self.text).strip()))
      if s:
        self.out.feed(s+'\n')
        self.text = []
    return
  
  def start_unknown(self, tag, attrs):
    if tag in self.ignored_tags:
      self.ignore += 1
    if tag in self.newline_tags:
      self.flush(True)
    return
  
  def end_unknown(self, tag):
    if tag in self.ignored_tags:
      self.ignore -= 1
    return
  
  def handle_data(self, data):
    if not self.ignore:
      self.text.append(data)
    return
  
  def finish(self):
    self.flush()
    self.out.close()
    return


# main
if __name__ == "__main__":
  import getopt, urllib
  class out:
    def __init__(self, charset):
      self.encoder = getencoder(charset)
      return
    def close(self): pass
    def feed(self, s):
      sys.stdout.write(self.encoder(s, 'replace')[0])
      sys.stdout.flush()
      return
  def usage():
    print 'usage: html2txt.py [-c charset_in] [-C charset_out] files ...'
    sys.exit(2)
  try:
    (opts, args) = getopt.getopt(sys.argv[1:], 'c:C:')
  except getopt.GetoptError:
    usage()
  (charset_in, charset_out) = ('utf-8', 'utf-8')
  for (k,v) in opts:
    if k == '-c': charset_in = v
    elif k == '-C': charset_out = v
  if not args: args = ['-']
  for url in args:
    if url == '-':
      fp = sys.stdin
    elif url.startswith('http:') or url.startswith('ftp:'):
      fp = urllib.urlopen(url)
    else:
      fp = file(url)
    p = HTMLParser3(HTMLTextHandler(out(charset_out)), charset=charset_in)
    p.feedfile(fp).close()
    fp.close()
