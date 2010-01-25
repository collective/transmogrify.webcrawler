#!/usr/bin/env python
#
# htmlparser3.py
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
from sgmlparser3 import SGMLParser3
from htmlutils import getdecoder, BLOCK_TAGS, CDATA_TAGS, INLINE_IMMED_TAGS, NON_NESTED_TAGS, VALID_TAGS
stderr = sys.stderr

__all__ = [ 'HTMLHandler', 'HTMLParser3' ]


##  HTMLHandler
##
class HTMLHandler:
  '''
  HTMLHandler class receive All text data and SGML entities
  are converted to Unicode strings and passed to handle_data
  method.  Comments are also converted to Unicode strings and
  passed to handle_comment method. At every occurrence of TAG,
  start_TAG and end_TAG are called. If there is no such a method,
  start_unknown and end_unknown are called at the beginning tag and
  the end tag respectively.
  '''

  def set_charset(self, charset):
    return

  def start_unknown(self, tag, attrs):
    '''Handles the beginning of an unknown tag.'''
    print 'HTMLHandler: start_unknown: tag=%s, attrs=%r' % (tag, attrs)
    return
  
  def end_unknown(self, tag):
    '''Handles the end of an unknown tag.'''
    print 'HTMLHandler: end_unknown: tag=%s' % tag
    return
  
  def do_unknown(self, tag, attrs):
    '''Handles the end of an unknown immediate tag.'''
    print 'HTMLHandler: do_unknown: tag=%s' % tag
    return
  
  def handle_data(self, data):
    '''Handles text data and SGML entities.'''
    print 'HTMLHandler: handle_data: data=%r' % data
    return
  
  def finish(self):
    '''Called when the parser reaches at the end of file.'''
    return


##  HTMLParser3
##
##     <HTML>, <BODY>, <HEAD>, <BASE>, .. only once in a document.
##     <BR>, <AREA>, <LINK>, <IMG>, <PARAM>, <INPUT>, <COL>, <FRAME>, <META> .. no data inside.
##     <HR>, no data inside, but end previous <p>
##     <P>, ... end previous <p>
##     block: <h?><ul><ol><dl><pre><div><center><noscript><noframes>
##            <blockquote><form><hr><table><fieldset><address> end previous <p>
##     <DT>, <DD> ... end previous <dd> or <dt>
##     <LI>, ... end previous <li>
##     <OPTION>, ... end previous <OPTION>
##     <THEAD>, <TFOOT>, <TBODY>, ... end previous <THEAD>, <TFOOT>, <TBODY>
##     <COLGROUP>, ... end previous <COLGROUP>,
##     <TR>, ... end previous <TR>, <TD> or <TH>
##     <TD>, <TH> ... end previous <TD> or <TH>
##
class HTMLParser3(SGMLParser3):
  '''
  An HTML parser class which handles internationalized text.
  '''

  TAGSTOP = {
    'td':('tr','table',),
    'tr':('table',),
    'li':('ul','ol',),
    'dt':('dl',),
    'dd':('dl',)
    }

  def __init__(self, handler, charset=None, debug=0):
    SGMLParser3.__init__(self)
    self.debug = debug
    self.handler = handler
    self.linepos = 0
    self.decoder = getdecoder(charset or 'iso-8859-1')
    self.charset = charset
    self.tagstack = []
    if self.debug:
      print >>stderr, 'HTMLParser3: start'
    return
  
  def set_charset(self, charset):
    '''Changes the current charset and codec.'''
    if self.charset: return
    try:
      self.decoder = getdecoder(charset)
    except LookupError:
      return
    self.charset = charset
    self.handler.set_charset(charset)
    if self.debug:
      print >>stderr, 'set_charset: %s' % charset
    return

  def handle_characters(self, data):
    '''Handles text.'''
    if self.debug:
      print >>stderr, 'handle_data: %r' % data
    self.handler.handle_data(data)
    return

  def handle_directive(self, name, attrs):
    return
  
  def handle_decl(self, data):
    if self.debug:
      print >>stderr, 'handle_decl: %r' % data
    return

  CHARSET_FIND = re.compile(r'charset\s*=\s*([^">;\s]+)', re.I)
  def hook_charset(self, attrs):
    if ('http-equiv' in attrs) and ('content' in attrs):
      m = self.CHARSET_FIND.search(attrs['content'])
      if m:
        self.set_charset(m.group(1))
    elif 'charset' in attrs:
      self.set_charset(attrs['charset'])
    return

  def handle_start_tag(self, tag, attrs):
    if tag not in VALID_TAGS:
      if self.debug:
        print >>stderr, 'ignored:', tag
      return
    if self.debug:
      print >>stderr, 'start: <%s> attrs=%r' % (tag, attrs)
    attrs = dict(attrs)
    if tag in INLINE_IMMED_TAGS:
      if tag == 'hr':
        self.end_previous(('p',), BLOCK_TAGS)
      elif tag == 'meta':
        self.hook_charset(attrs)
      # dispatch
      methodname = 'do_'+tag
      if hasattr(self.handler, methodname):
        getattr(self.handler, methodname)(tag, attrs)
      else:
        self.handler.do_unknown(tag, attrs)
    else:
      # sorry for yucky tuple syntax... :(
      if tag in ('dt', 'dd'):
        self.end_previous(('dt', 'dd',), ('dl',))
      elif tag == 'li':
        self.end_previous(('li',), ('ul','ol',))
      elif tag == 'option':
        self.end_previous(('option',), ('select',))
      elif tag in ('thead', 'tfoot', 'tbody'):
        self.end_previous(('thead', 'tfoot', 'tbody',), ('table',))
      elif tag == 'colgroup':
        self.end_previous(('colgroup',), ('table',))
      elif tag == 'tr':
        self.end_previous(('tr',), ('table',))
      elif tag in ('td', 'th'):
        self.end_previous(('td', 'th',), ('tr', 'table',))
      elif tag in BLOCK_TAGS:
        self.end_previous(('p',), BLOCK_TAGS)
      elif tag in CDATA_TAGS:
        self.start_cdata(tag)
      if tag not in NON_NESTED_TAGS:
        self.tagstack.append(tag)
      # dispatch
      methodname = 'start_'+tag
      if hasattr(self.handler, methodname):
        getattr(self.handler, methodname)(tag, attrs)
      else:
        self.handler.start_unknown(tag, attrs)
    return

  def handle_end_tag(self, tag, _):
    if tag not in VALID_TAGS:
      if self.debug:
        print >>stderr, 'ignored:', tag
      return
    if tag in NON_NESTED_TAGS:
      methodname = 'end_'+tag
      if hasattr(self.handler, methodname):
        getattr(self.handler, methodname)(tag)
      else:
        self.handler.end_unknown(tag)        
    elif tag not in INLINE_IMMED_TAGS:
      self.end_previous((tag,), self.TAGSTOP.get(tag, ()))
    return

  def end_previous(self, tags, stops):
    for i in range(len(self.tagstack)-1, -1, -1):
      t = self.tagstack[i]
      if t in tags:
        for tag in self.tagstack[i:]:
          if self.debug:
            print >>stderr, 'end: </%s>' % tag
          methodname = 'end_'+tag
          if hasattr(self.handler, methodname):
            getattr(self.handler, methodname)(tag)
          else:
            self.handler.end_unknown(tag)        
        self.tagstack = self.tagstack[:i]
        break
      elif t in stops:
        break
    return

  def close(self):
    SGMLParser3.close(self)
    while self.tagstack:
      self.end_previous(self.tagstack, ())
    if self.debug:
      print >>stderr, 'HTMLParser3: close'
    return self.handler.finish()

  def feed_file(self, fp, pos=0):
    self.linepos = pos
    for line in fp:
      self.uniline = self.decoder(line, 'replace')[0]
      self.feed(self.uniline)
      self.linepos += len(line)
    return self

  def feed_byte(self, byte, pos=0):
    try:
      from cStringIO import StringIO
    except ImportError:
      from StringIO import StringIO
    return self.feed_file(StringIO(byte), pos)


# test
if __name__ == '__main__':
  import getopt
  def usage():
    print 'usage: htmlparser3.py [-d] [-c charset] [url ...]'
    sys.exit(2)
  try:
    (opts, args) = getopt.getopt(sys.argv[1:], 'dc:')
  except getopt.GetoptError:
    usage()
  (debug, charset) = (0, None)
  for (k, v) in opts:
    if k == '-d': debug += 1
    elif k == '-c': charset = v
  for fname in args:
    parser = HTMLParser3(HTMLHandler(), charset=charset, debug=debug)
    fp = file(fname)
    parser.feed_file(fp)
    parser.close()
    fp.close()
