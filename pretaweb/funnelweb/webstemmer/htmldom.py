#!/usr/bin/env python
#
# htmldom.py
#
#  Copyright (c) 2005 onward  Yusuke Shinyama <yusuke at cs dot nyu dot edu>
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

import sys
from htmlparser3 import HTMLParser3, HTMLHandler
from htmlutils import getencoder, quotestr, attr2str, concat, \
     CDATA_TAGS, INLINE_IMMED_TAGS, FORM_FIELD_TAGS, NON_NESTED_TAGS, NON_DISPLAYED_TAGS, BREAK_LINE_TAGS
from style import Style, StyleSheet, ActiveStyleSheet, parse_inline

global debug
debug = 0


##  HTMLElement
##
class HTMLElement:
  """
  This class represents an HTML element.
  This object has the following public attributes.
  
  tag: the name of the element.
  root: the root element which is the whole HTML page.
  parent: the parent element.
  children: a list of child elements.
  attrs: dictionary which contains attributes.
  active: boolean flag which indicates whether this element is
          still under construction.
  """
  
  def __init__(self, root, tag, children=None, attrs=None, parent=None, active=True):
    """Creates an instance of the HTMLElement class.
    """
    self.root = root
    self.tag = str(tag)  # not unicode object!
    self.parent = parent
    self.active = active
    if attrs:
      self.attrs = attrs.copy()
    else:
      self.attrs = {}
    if children != None:
      self.children = children[:]
      for c in children:
        if isinstance(c, HTMLElement):
          c.parent = self
    else:
      self.children = None
    return
  
  def __repr__(self):
    return '<%s%s>' % (self.tag, ''.join( ' %s=%r' % (k,v) for (k,v) in self.attrs.iteritems() ))

  def __iter__(self):
    return iter(self.children)

  def __getitem__(self, k):
    return self.attrs.get(k)

  def __setitem__(self, k, v):
    self.attrs[str(k)] = v
    return

  def get(self, *keys):
    return tuple( self.attrs.get(k) for k in keys )

  def dup(self):
    return HTMLElement(self.root, self.tag, self.children, self.attrs,
                       self.parent, self.active)

  def finish(self):
    self.active = False
    if '_contexts' in self.attrs:
      del self.attrs['_contexts']
    return self
  
  def set_style(self, stylesheet):
    if not stylesheet: return
    attrs = self.attrs
    tags = [u'', self.tag]
    if 'class' in attrs:
      x = attrs['class']
      tags += [ t+'.'+x for t in tags ]
    if 'id' in attrs:
      x = attrs['id']
      tags += [ t+'#'+x for t in tags ]
    (style, contexts) = stylesheet.lookup(tags, self.parent['_contexts'])
    self.attrs['_contexts'] = contexts
    if 'style' in attrs:
      style = Style(style)
      parse_inline(style, attrs['style'])
    self.attrs['_style'] = style
    return

  def walk(self, cut=lambda d,e: False, endtag=False, depth=0):
    if cut(depth, self): return
    yield (depth, self)
    if not self.children: return
    depth += 1
    for c in self.children:
      if isinstance(c, HTMLElement):
        for x in c.walk(cut, endtag, depth):
          yield x   # relay
      elif isinstance(c, basestring):
        yield (depth, c)
      else:
        raise TypeError('Invalid object: %r in %r' % (c, self))
    if endtag:
      yield (-depth, self)
    return

  def dump(self):
    """
    Reformat everything.
    """
    for (d,e) in self.walk(endtag=True, depth=1):
      if isinstance(e, basestring):
        yield e
      elif 0 < d:
        # start tag
        if e.tag == 'comment':
          yield u'<!--'
        else:
          yield u'<%s%s>' % (e.tag, attr2str(e.attrs.iteritems()))
      else:
        # end tag
        if e.tag == 'comment':
          yield u'-->'
        else:
          yield u'</%s>' % e.tag
    return

  def get_text(self, ignore_tags=NON_DISPLAYED_TAGS, br_tags=BREAK_LINE_TAGS):
    for (_,e) in self.walk(cut=lambda _,e: e.tag in ignore_tags):
      if isinstance(e, basestring):
        yield e
      else:
        tag = e.tag
        if tag in br_tags:
          yield u'\n'
        if tag == 'img' and ('alt' in e.attrs):
          yield e.attrs['alt']
    return

  def get_links(self, normalize=False):
    """
    Generate the list of href links and its anchor text in the element.
    When normalize is set, the relative url is normalized based on the documentbase.
    """
    from urllib import unquote
    for (_,e) in self.walk():
      if isinstance(e, HTMLElement) and e.tag == 'a' and e['href']:
        url = unquote(e['href'])
        if normalize:
          url = self.root.normalize_url(url)
        yield (e.get_text(), url)
    return
  
  def add_child(self, e):
    """
    Add a child HTMLElement.
    """
    if self.children == None:
      raise TypeError('this element cannot have a child: %r' % self)
    if isinstance(e, basestring) and self.children and isinstance(self.children[-1], basestring):
      self.children[-1] += e
    else:
      self.children.append(e)
    if isinstance(e, HTMLElement):
      e.parent = self
    return self


##  Utilities
##
def first(seq, x=None):
  for x in seq: break
  return x

def last(seq, x=None):
  for x in seq: pass
  return x

def tag(x):
  return isinstance(x, HTMLElement) and x.tag

def text(x):
  if isinstance(x, basestring):
    return x
  elif isinstance(x, HTMLElement):
    return ''.join(x.get_text())
  else:
    raise TypeError(x)

# check the structure is correct.
def validate(root, e0):
  # check if every node (except the root) has a parent.
  for (_,e) in e0.walk():
    if isinstance(e, basestring): continue
    if e != root and (not e.parent or (e not in e.parent.children)):
      raise TypeError('Orphaned node: %r in %r' % (e, e.parent))
    if not e.children: continue
    # check if all my children belong to me.
    for c in e.children:
      if isinstance(c, HTMLElement) and c.parent != e:
        raise TypeError('Invalid child: %r in %r' % (c, e))
  return


##  HTMLForm
##
class HTMLForm:
  
  def __init__(self, root, attrs):
    self.root = root
    self.attrs = attrs
    self.fields = []
    return
  
  def add_field(self, field):
    self.fields.append(field)
    field.form = self
    return


##  HTMLRootElement
##
class HTMLRootElement(HTMLElement):
  """A special element which contains the whole HTML document.
  """

  def __init__(self, charset=None, base_href=None):
    HTMLElement.__init__(self, self, 'html', [])
    self.charset = charset
    self.base_href = base_href
    self.forms = []
    self.head = HTMLElement(self, 'head', [])
    return

  def dup(self):
    raise TypeError('HTMLRootElement cannot be duplicated.')

  def set_root_attrs(self, attrs):
    self.attrs = attrs
    return

  def set_root_charset(self, charset):
    self.charset = charset
    return

  def get_title(self):
    head = self.children[0]
    title = first( e for e in head.walk() if e.tag == 'title' )
    if not title: return None
    return ''.join(title.get_text())

  def add_header(self, e):
    self.head.add_child(e)
    if e.tag == 'base':
      if self.base_href:
        e['href'] = self.base_href
      else:
        self.base_href = e['href']
    return

  # normalize_url(url)
  def normalize_url(self, url):
    from urlparse import urljoin
    """Convert a relative URL to an absolute one."""
    return urljoin(self.base_href, url)

  def finish(self):
    HTMLElement.finish(self)
    if not first( e for e in self.head if e.tag == 'base' ):
      base = HTMLElement(self, 'base', attrs={ 'href': self.base_href }).finish()
      self.head.add_child(base)
    self.head.finish()
    body = HTMLElement(self, 'body', self.children)
    self.children = []
    self.add_child(self.head)
    self.add_child(body)
    return self


##  HTMLDocumentBuilder
##
class HTMLDocumentBuilder(HTMLHandler):
  
  def __init__(self, base_href=None, stylesheet=None):
    self.root = HTMLRootElement(base_href=base_href)
    self.curform = None
    self.curstack = [self.root]
    self.stylesheet = stylesheet
    return

  def set_charset(self, charset):
    self.root.set_root_charset(charset)
    return

  def handle_data(self, s):
    assert self.curstack
    self.curstack[-1].add_child(s)
    return

  def do_unknown(self, tag, attrs):
    tag = str(tag)
    attrs = dict( (k.encode('ascii','ignore'),v) for (k,v) in attrs.iteritems() )
    e = HTMLElement(self.root, tag, None, attrs)
    if tag == 'link':
      self.root.add_header(e)
      if self.stylesheet and attrs.get('rel') == 'stylesheet' and 'href' in attrs:
        self.stylesheet.import_url(attrs.get('href'), attrs.get('media'))
    elif tag == 'base':
      self.root.add_header(e)
    elif tag == 'meta':
      self.root.add_header(e)
    else:
      self.curstack[-1].add_child(e)
      e.set_style(self.stylesheet)
    return

  def start_unknown(self, tag, attrs):
    #print "start:", tag, attrs
    tag = str(tag)
    attrs = dict( (str(k),v) for (k,v) in attrs.iteritems() )
    if tag == 'html':
      self.root.set_root_attrs(attrs)
    elif tag == 'form':
      self.curform = HTMLForm(self.root, attrs)
      self.root.forms.append(self.curform)
    elif tag in NON_NESTED_TAGS:
      pass
    else:
      e = HTMLElement(self.root, tag, [], attrs)
      if tag == 'title':
        self.root.add_header(e)
      else:
        self.curstack[-1].add_child(e)
        e.set_style(self.stylesheet)
      self.curstack.append(e)
      if self.curform and tag in FORM_FIELD_TAGS:
        self.curform.add_field(e)
    return

  def end_unknown(self, tag):
    tag = str(tag)
    if tag == 'html':
      pass
    elif tag == 'form':
      self.curform = None
    elif tag in NON_NESTED_TAGS:
      pass
    else:
      self.curstack[-1].finish()
      if tag == 'style' and self.stylesheet:
        self.stylesheet.parse(''.join(self.curstack[-1].children))
        (style, _) = self.stylesheet.lookup(['',u'html',u'body'])
        self.root.attrs['_style'] = style
      self.curstack.pop()
    return

  def finish(self):
    assert len(self.curstack) == 1 and self.curstack[0] == self.root, self.curstack
    self.root.finish()
    self.curstack.pop()
    return self.root



##  Utilities
##
def parse(x, base_href=None, charset=None, stylesheet=None):
  builder = HTMLDocumentBuilder(base_href=base_href, stylesheet=stylesheet)
  parser = HTMLParser3(builder, charset=charset)
  if isinstance(x, unicode):
    parser.feed_unicode(x)
    e = parser.close()
  elif isinstance(x, str):
    parser.feed_byte(x)
    e = parser.close()
  else:
    parser.feed_file(x)
    e = parser.close()
    x.close()
  return e


# main
if __name__ == '__main__':
  import getopt, agent
  def usage():
    print 'usage: htmldom.py [-d] [-b base_href] [-c charset_in] [-C codec_out] [url ...]'
    sys.exit(2)
  try:
    (opts, args) = getopt.getopt(sys.argv[1:], 'dc:C:b:')
  except getopt.GetoptError:
    usage()
  (charset_in, codec_out, base_href) = ('iso-8859-1', 'euc-jp', '')
  for (k, v) in opts:
    if k == '-d': debug += 1
    elif k == '-c': charset_in = v
    elif k == '-C': codec_out = v
    elif k == '-b': base_href = v
  encoder = getencoder(codec_out)
  for url in args:
    agent = agent.Agent(debug=sys.stdout)
    (fp, content_type, charset) = agent.get(url)
    stylesheet = ActiveStyleSheet(agent, base_href=(base_href or url))
    root = parse(fp, base_href=url, charset=(charset or charset_in), stylesheet=stylesheet)
    fp.close()
    stylesheet.dump()
    validate(root, root)
    if debug:
      for (i,e) in root.walk():
        sys.stdout.write('  '*i+repr(e)+'\n')
    else:
      for c in root.dump():
        sys.stdout.write(encoder(c, 'xmlcharrefreplace')[0])

