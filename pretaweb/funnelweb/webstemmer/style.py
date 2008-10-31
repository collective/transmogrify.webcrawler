#!/usr/bin/env python
import re


##  Misc.
##
def is_cssnumber(x):
  return isinstance(x, tuple) and len(x) == 2 and (isinstance(x[0], int) or isinstance(x[0], float))

def is_cssstring(x):
  return isinstance(x, basestring) and (x[0] in '(\'"')

def is_csssymbol(x):
  return isinstance(x, basestring) and (x[0] not in '@#(\'"')

def filter_numbers(args):
  return [ x for x in args if is_cssnumber(x) ]

def filter_symbols(args):
  return [ x for x in args if is_csssymbol(x) ]

def get_color(args):
  if args[0] == 'rgb':
    args = filter_numbers(args[1:])
    if 3 <= len(args):
      return args[:3]
  return args[0]

# returns (top, left, right, bottom)
def fill_args(args):
  if len(args) == 1:                    # top & left & right & bottom
    (top, left, right, bottom) = (args[0], args[0], args[0], args[0])
  elif len(args) == 2:                  # top & bottom, left & right
    (top, left, right, bottom) = (args[0], args[1], args[1], args[0])
  elif len(args) == 3:                  # top, left & right, bottom
    (top, left, right, bottom) = (args[0], args[1], args[1], args[2])
  else:                                 # top, right, bottom, left
    (top, left, right, bottom) = (args[0], args[3], args[1], args[2])
  return (top, left, right, bottom)


##  Style
##

# Style(parent, **args)
# Style(parent)
# Style()

INHERITABLE = set(
  'direction line_height quotes list_style_type list_style_image list_style_position '
  'page_break_inside page orphans widows color font_family font_style '
  'font_variant font_weight font_stretch font_size font_size_adjust text_indent '
  'text_align object_align letter_spacing word_spacing text_transform white_space caption_side '
  'border_collapse border_spacing empty_cells speak_header cursor volume speak azimuth '
  'elevation speech_rate voice_family pitch pitch_range stress richness '
  'speak_punctuation speak_numeral'.split(' '))

RELATIVE = set([
  'margin_top',
  'margin_right',
  'margin_bottom',
  'margin_left',
  'padding_top',
  'padding_right',
  'padding_bottom',
  'padding_left',
  'top',
  'right',
  'bottom',
  'left',
  ])

def percent_parent_width(parent, v):
  return parent.width * v
def percent_parent_height(parent, v):
  return parent.height * v
def percent_line_height(parent, v):
  return parent.placer.base_em * v

PERCENTAGE = {
  'margin_top': percent_parent_height,
  'margin_right': percent_parent_width,
  'margin_bottom': percent_parent_height,
  'margin_left': percent_parent_width,
  'padding_top': percent_parent_height,
  'padding_right': percent_parent_width,
  'padding_bottom': percent_parent_height,
  'padding_left': percent_parent_width,
  'top': percent_parent_height,
  'right': percent_parent_width,
  'bottom': percent_parent_height,
  'left': percent_parent_width,
  'width': percent_parent_width,
  'min_width': percent_parent_width,
  'max_width': percent_parent_width,
  'height': percent_parent_height,
  'min_height': percent_parent_height,
  'max_height': percent_parent_height,
  'line_height': percent_line_height,
  'vertical_align': percent_line_height,
  'background_position': percent_parent_width,
  'font_size': percent_parent_width,
  'text_indent': percent_parent_width,
  }

class Style(object):

  def __init__(self, parent=None, **args):
    self.parent = parent
    self.values = args.copy()
    return

  def iteritems(self):
    values = self.values.copy()
    self = self.parent
    while self:
      for (k,v) in self.values.iteritems():
        if k not in values:
          values[k] = v
      self = self.parent
    return values.iteritems()

  def __repr__(self):
    return '<Style: %s>' % (', '.join( '%s=%r' % (k,v) for (k,v) in self.iteritems()
                                       if not k.startswith('_') ))

  def __getitem__(self, k):
    if k in self.values:
      return self.values[k]
    if self.parent:
      return self.parent[k]
    return None

  def copy(self):
    return Style(self.parent, **self.values)

  def override(self, parent_component, style, default_style):
    dest = Style(default_style)
    for (k,v) in self.iteritems():
      if k in INHERITABLE:
        dest.values[k] = v
    if style:
      for (k,v) in style.iteritems():
        if isinstance(v, tuple):
          (v,unit) = v
          if unit == '%':
            v = int(PERCENTAGE[k](parent_component, v*0.01))
          elif unit == 'em':
            v = int(parent_component.placer.base_em * v)
          elif unit == 'pt':
            v = int(parent_component.placer.base_pt * v)
        if (k in RELATIVE) and (k in dest.values):
          dest.values[k] += v
        else:
          dest.values[k] = v
    return dest

  def add_decl(self, decl, _=None):
    for (k,v) in decl.iteritems():
      a = 'set_'+k
      if hasattr(self, a):
        getattr(self, a)(v)
    return

  def _set_color(self, args, prop):
    if not args: return
    self.values[prop] = get_color(args)
    return
  
  def _set_number(self, args, prop):
    args = filter_numbers(args)
    if not args: return
    (v,unit) = args[0]
    self.values[prop] = v
    return
    
  def _set_number_unit(self, args, prop):
    args = filter_numbers(args)
    if not args: return
    self.values[prop] = args[0]
    return
    
  def _set_symbol(self, args, prop):
    args = filter_symbols(args)
    if not args: return
    self.values[prop] = args[0]
    return

  # XXX combo
  #def set_font(self, args): self._set_symbol(args, 'font')
  def set_background(self, args): self._set_color(args, 'background')
  
  def set_background_color(self, args): self._set_color(args, 'background_color')
  #def set_background_image(self, args):
  def set_background_repeat(self, args): self._set_symbol(args, 'background_repeat')
  def set_background_attachment(self, args): self._set_symbol(args, 'background_attachment')
  def set_background_position(self, args): self._set_symbol(args, 'background_position')

  def set_font_family(self, args): self._set_symbol(args, 'font_family')
  def set_font_style(self, args): self._set_symbol(args, 'font_style')
  def set_font_variant(self, args): self._set_symbol(args, 'font_variant')
  def set_font_weight(self, args): self._set_symbol(args, 'font_weight')
  def set_font_stretch(self, args): self._set_symbol(args, 'font_stretch')
  # percentage refers to the parent font_size.
  def set_font_size(self, args): self._set_number_unit(args, 'font_size')
  
  # various layout props.
  def set_color(self, args): self._set_color(args, 'color')
  def set_top(self, args): self._set_number_unit(args, 'top')
  def set_left(self, args): self._set_number_unit(args, 'left')
  def set_right(self, args): self._set_number_unit(args, 'right')
  def set_bottom(self, args): self._set_number_unit(args, 'bottom')

  def set_width(self, args): self._set_number_unit(args, 'width')
  def set_height(self, args): self._set_number_unit(args, 'min_height')
  def set_min_width(self, args): self._set_number_unit(args, 'min_width')
  def set_min_height(self, args): self._set_number_unit(args, 'height')
  def set_max_width(self, args): self._set_number_unit(args, 'max_width')
  def set_max_height(self, args): self._set_number_unit(args, 'max_height')
  
  # percentage refers to the font_size.
  def set_line_height(self, args): self._set_number_unit(args, 'line_height')
  # percentage refers to the line_height.
  def set_vertical_align(self, args): self._set_number_unit(args, 'vertical_align')
  def set_text_indent(self, args): self._set_number_unit(args, 'text_indent')
  def set_list_padding(self, args): self._set_number(args, 'list_padding')
  def set_para_space(self, args): self._set_number_unit(args, 'para_space')
  
  def set_text_align(self, args): self._set_symbol(args, 'text_align')
  def set_text_decolation(self, args): self._set_symbol(args, 'text_decolation')
  def set_text_underline_position(self, args): self._set_symbol(args, 'text_underline_position')

  def set_display(self, args): self._set_symbol(args, 'display')
  def set_position(self, args): self._set_symbol(args, 'position')
  def set_float(self, args): self._set_symbol(args, 'float')
  def set_clear(self, args): self._set_symbol(args, 'clear')
  def set_overflow(self, args): self._set_symbol(args, 'overflow')
  def set_visibility(self, args): self._set_symbol(args, 'visibility')

  # padding
  def set_padding(self, args):
    args = filter_numbers(args)
    if not args: return
    (self.values['padding_top'], self.values['padding_left'],
     self.values['padding_right'], self.values['padding_bottom']) = fill_args(args)
    return
  def set_padding_top(self, args): self._set_number_unit(args, 'padding_top')
  def set_padding_left(self, args): self._set_number_unit(args, 'padding_left')
  def set_padding_right(self, args): self._set_number_unit(args, 'padding_right')
  def set_padding_bottom(self, args): self._set_number_unit(args, 'padding_bottom')
  
  # margin
  def set_margin(self, args):
    args = filter_numbers(args)
    if not args: return
    (self.values['margin_top'], self.values['margin_left'],
     self.values['margin_right'], self.values['margin_bottom']) = fill_args(args)
    return
  def set_margin_top(self, args): self._set_number_unit(args, 'margin_top')
  def set_margin_left(self, args): self._set_number_unit(args, 'margin_left')
  def set_margin_right(self, args): self._set_number_unit(args, 'margin_right')
  def set_margin_bottom(self, args): self._set_number_unit(args, 'margin_bottom')
    
  # border-width
  def set_border_width(self, args):
    args = filter_numbers(args)
    if not args: return
    (self.values['border_width_top'], self.values['border_width_left'],
     self.values['border_width_right'], self.values['border_width_bottom']) = fill_args(args)
    return
  def set_border_width_top(self, args): self._set_number(args, 'border_width_top')
  def set_border_width_left(self, args): self._set_number(args, 'border_width_left')
  def set_border_width_right(self, args): self._set_number(args, 'border_width_right')
  def set_border_width_bottom(self, args): self._set_number(args, 'border_width_bottom')

  # border-style
  def set_border_style(self, args):
    args = filter_symbols(args)
    if not args: return
    (self.values['border_style_top'], self.values['border_style_left'],
     self.values['border_style_right'], self.values['border_style_bottom']) = fill_args(args)
    return
  def set_border_style_top(self, args): self._set_number(args, 'border_style_top')
  def set_border_style_left(self, args): self._set_number(args, 'border_style_left')
  def set_border_style_right(self, args): self._set_number(args, 'border_style_right')
  def set_border_style_bottom(self, args): self._set_number(args, 'border_style_bottom')

  # border-color
  def set_border_color(self, args, props=('top','left','right','bottom')):
    if not args: return
    color = get_color(args)
    for prop in props:
      self.values['border_color_'+prop] = color
    return
  def set_border_color_top(self, args): self.set_border_color(args, ('top',))
  def set_border_color_left(self, args): self.set_border_color(args, ('left',))
  def set_border_color_right(self, args): self.set_border_color(args, ('right',))
  def set_border_color_bottom(self, args): self.set_border_color(args, ('bottom',))

  # border
  def set_border(self, args, props=('top','left','right','bottom')):
    if len(args) < 3 or not is_cssnumber(args[0]) or not is_csssymbol(args[1]): return
    (width, style, color) = (args[0], args[1], get_color(args[2:]))
    for prop in props:
      self.values['border_width_'+prop] = width
      self.values['border_style_'+prop] = style
      self.values['border_color_'+prop] = color
    return
  def set_border_top(self, args): self.set_border(args, ('top',))
  def set_border_left(self, args): self.set_border(args, ('left',))
  def set_border_right(self, args): self.set_border(args, ('right',))
  def set_border_bottom(self, args): self.set_border(args, ('bottom',))


##  StyleSheet
##
class StyleSheet:
  
  def __init__(self, device=None):
    self.style = {}
    self.state = {}
    self.device = device
    self.enabled = True
    return

  def dup(self):
    stylesheet = StyleSheet()
    stylesheet.copy(self)
    return stylesheet

  def copy(self, stylesheet):
    self.style = stylesheet.style.copy()
    self.state = stylesheet.state.copy()
    self.device = stylesheet.device
    self.enabled = stylesheet.enabled
    return
  
  def parse(self, s, charset=None):
    if charset:
      s = unicode(s, charset, 'replace')
    CSSParser(self).feed(CSSTokenizer().feed(s))
    return
  
  def parse_lines(self, lines, charset=None):
    tokenizer = CSSTokenizer()
    parser = CSSParser(self)
    for s in lines:
      if charset:
        s = unicode(s, charset, 'replace')
      parser.feed(tokenizer.feed(s))
    return
  
  def import_url(self, url, media_spec=None):
    return

  def dump(self):
    for (context,tag) in sorted(self.style.iterkeys()):
      decl = self.style[(context,tag)]
      print '%s/%s' % (context, tag)
      def f(x):
        if is_cssnumber(x):
          (x,u) = x
          if isinstance(x, float):
            return '%.1f%s' % (x,u)
          else:
            return '%d%s' % (x,u)
        else:
          return x
      for (k,v) in decl.iteritems():
        print '\t%s: %s' % (k, ' '.join( f(x) for x in v ))
      print
    return

  def switch_media(self, media_spec):
    if not self.device: return
    self.enabled = True
    if not media_spec: return
    for media in media_spec:
      if media == 'all' or self.device.media_type == media:
        return
    self.enabled = False
    return

  def add_decl(self, decl, selectors):
    if not self.enabled: return
    for sel in selectors:
      k = (None, None)
      context = ''
      for tag in sel:
        if tag == '>':
          context += '>'
          continue
        if tag == '*':
          tag = ''
        if context and (k not in self.state):
          self.state[k] = 1
        k = (context,tag)
        context += '/'+tag
      if k in self.style:
        self.style[k].update(decl)
      else:
        self.style[k] = decl
    return

  def lookup(self, tags, contexts=None):
    if not contexts:
      contexts1 = ['']
      contexts2 = set(contexts1)
    else:
      (contexts0, contexts1) = contexts
      contexts2 = contexts0.union(contexts1)
    dic = {}
    new = set()
    #print 'Lookup: (%s|%s>) + (%s)' % (','.join(contexts2), ','.join(contexts1), ','.join(tags)),
    for c in list(contexts2):
      for t in tags:
        if (c,t) in self.style:
          dic.update(self.style[(c,t)])
        if (c,t) in self.state:
          if c and (c in contexts2):
            contexts2.remove(c)
          new.add(c+'/'+t)
    for c in contexts1:
      c += '>'
      for t in tags:
        if (c,t) in self.style:
          dic.update(self.style[(c,t)])
        if (c,t) in self.state:
          if c and (c in contexts2):
            contexts2.remove(c)
          new.add(c+'/'+t)
    #print '-> (%s): %r' % (','.join(contexts2), dic)
    style = None
    if dic:
      style = Style()
      style.add_decl(dic)
    return (style, (contexts2, new))


##  CSSTokenizer
##
END_STRING = {
  u'"': re.compile(ur'["\\]'),
  u"'": re.compile(ur"['\\]"),
  u'(': re.compile(ur'[)\\]')
  }
NEXT_TOKENS = re.compile(ur'/\*|<!--|-->|~=|\|=|\n|\S')
END_COMMENT = re.compile(ur'\*/')
START_IDENT_NUMBER = re.compile(ur'[-\*#@\.0-9\w]', re.UNICODE)
END_IDENT_NUMBER = re.compile(ur'[^-.%\w]', re.UNICODE)
NUMBER = re.compile(ur'^(-?[0-9]*\.?[0-9]+)([a-z%]*)$')
UNICODE_HEX = re.compile(ur'[a-fA-F0-9]+\s?')

class CSSTokenizer:

  def __init__(self):
    self.parse1 = self.parse_main
    return

  def feed(self, s):
    assert isinstance(s, unicode)
    i = 0
    self.tokens = []
    while 0 <= i:
      (self.parse1, i) = self.parse1(s, i)
    return self.tokens

  def parse_main(self, x, i0):
    m = NEXT_TOKENS.search(x, i0)
    if not m: return (self.parse_main, -1)
    w = m.group(0)
    if w == u'\n':
      self.tokens.append(w)
      return (self.parse_main, -1)
    if w == u'/*':
      return (self.skip_comment, m.end(0))
    if w == u'"' or w == u"'" or w == u'(':
      self.ident = w
      self.end_string = END_STRING[w]
      self.ignore_ending = 1
      return self.parse_string(x, m.end(0))
    if w == u'\\':
      self.ident = u''
      self.end_string = END_IDENT_NUMBER
      self.ignore_ending = 0
      return self.parse_string(x, m.start(0))
    if START_IDENT_NUMBER.match(w):            # not search!
      self.ident = w
      self.end_string = END_IDENT_NUMBER
      self.ignore_ending = 0
      return self.parse_string(x, m.end(0))
    self.tokens.append(w)
    return (self.parse_main, m.end(0))

  def skip_comment(self, x, i0):
    m = END_COMMENT.search(x, i0)
    if m:
      return (self.parse_main, m.end(0))
    return (self.skip_comment, -1)

  def parse_string(self, x, i0):
    while 1:
      m = self.end_string.search(x, i0)
      if not m:
        self.ident += x[i0:]
        i1 = -1
        break
      i1 = m.start(0)
      self.ident += x[i0:i1]
      if m.group(0) == u'\\':
        i1 = m.end(0)
        m = UNICODE_HEX.match(x, i1)    # not search!
        if m:
          self.ident += unichr(int(m.group(0), 16))
          i0 = m.end(0)
        else:
          self.ident += x[i1]
          i0 = i1+1
        continue
      # is it a number?
      m = NUMBER.match(self.ident)
      if m:
        n = m.group(1)
        try:
          if u'.' in n:
            n = float(n)
          else:
            n = int(n)
        except ValueError:
          n = 0
        unit = str(m.group(2))
        if unit == 'px': unit = ''
        self.tokens.append((n, unit))
      elif self.ident[0] in u'#(\'"':
        self.tokens.append(self.ident)
      else:
        self.tokens.append(self.ident.lower())
      return (self.parse_main, i1+self.ignore_ending)
    return (self.parse_string, i1)


##  CSSParser
##
class CSSParser:

  def __init__(self, stylesheet):
    self.stylesheet = stylesheet
    self.parse1 = self.parse_main
    self.selectors = []
    self.cursel = []
    return

  def feed(self, tokens):
    for t in tokens:
      # Do not change the value if None is returned.
      self.parse1 = self.parse1(t) or self.parse1
    return

  def feed_decl(self, tokens):
    self.prop = None
    self.args = []
    self.dic = {}
    parse1 = self.parse_decl0
    for t in tokens:
      # Do not change the value if None is returned.
      parse1 = parse1(t) or parse1
      if parse1 == self.parse_main: break
    self.stylesheet.add_decl(self.dic)
    return
    
  def fix_cursel(self):
    self.prop = None
    self.args = []
    self.dic = {}
    if not self.cursel: return
    sel = []
    tag = u''
    for x in self.cursel:
      if x == u':' or tag.endswith(u':'):
        tag += x
      else:
        if tag: sel.append(tag)
        tag = x
    sel.append(tag)
    self.selectors.append(sel)
    self.cursel = []
    return

  def parse_main(self, t):
    if not isinstance(t, basestring): return
    if t == u'{':
      self.fix_cursel()
      return self.parse_decl0
    if t == u'}':
      # assuming the end of "@media {...}"
      self.stylesheet.switch_media(None)
      return
    if t == u'@import':
      return self.parse_import
    if t == u'@media':
      self.args = []
      return self.parse_media
    if t == u'@page':
      return self.parse_page
    if t == u',':
      self.fix_cursel()
      return
    if t == u':' or t == u'>' or START_IDENT_NUMBER.match(t[0]):
      self.cursel.append(t)
    return

  def parse_decl0(self, t):
    if t == u':' and self.prop:
      return self.parse_decl1
    if t == u'}':
      self.stylesheet.add_decl(self.dic, self.selectors)
      self.selectors = []
      return self.parse_main
    if t == u'\n':
      return
    if isinstance(t, unicode):
      t = t.encode('ascii', 'replace')
    elif not isinstance(t, str):
      return
    self.prop = t
    self.args = []
    return

  def parse_decl1(self, t):
    if t == u';' or t == u'\n' or t == u'}':
      if self.args:
        self.dic[self.prop.replace('-','_')] = self.args
      if t == u'}':
        return self.parse_decl0(t)
      return self.parse_decl0
    self.args.append(t)
    return

  def parse_import(self, t):
    if t == u';' or t == u'\n':
      return self.parse_main
    elif isinstance(t, basestring) and (t[0] in u'\042\047('):
      self.stylesheet.import_url(t[1:])
    return
  
  def parse_media(self, t):
    if t == u'{':
      self.stylesheet.switch_media(self.args)
      return self.parse_main
    assert isinstance(t, unicode)
    self.args.append(t)
    return

  def parse_page(self, t):
    if t == u'}':
      return self.parse_main
    return


##  ActiveStyleSheet
##
class ActiveStyleSheet(StyleSheet):

  def __init__(self, agent=None, device=None):
    StyleSheet.__init__(self, device)
    self.agent = agent
    return

  def dup(self):
    stylesheet = ActiveStyleSheet()
    stylesheet.copy(self)
    return stylesheet

  def copy(self, stylesheet):
    StyleSheet.copy(self, stylesheet)
    self.agent = stylesheet.agent
    return 

  def set_base(self, base_href):
    self.base_href = base_href
    self.visited = set()
    return
  
  def import_url(self, url, media_spec=None):
    from urlparse import urljoin
    if not self.agent: return
    self.switch_media(media_spec)
    if not self.enabled: return
    url = urljoin(self.base_href, url)
    if url in self.visited: return
    self.visited.add(url)
    try:
      (fp, content_type, charset) = self.agent.get(url)
      base_href0 = self.base_href
      self.base_href = url
      self.parse_lines(fp, charset or 'iso-8859-1')
      self.base_href = base_href0
      fp.close()
    except IOError:
      pass
    return


##  Utilities
##
def parse_inline(style, s, charset=None):
  if charset:
    s = unicode(s, charset, 'replace')
  CSSParser(style).feed_decl(CSSTokenizer().feed(s+';'))
  return

def read_stylesheet(args=None):
  import fileinput
  stylesheet = StyleSheet()
  stylesheet.parse_lines(fileinput.input(args), 'iso-8859-1')
  stylesheet.dump()
  return

def basic_test():
  stylesheet = StyleSheet()
  stylesheet.parse_lines([
    u'p { background-color: white }\n',
    u'ul { background-color: bbb }\n',
    u'ul li { background-color: ccc; top:40pt }\n',
    u'ul>li { background-color: ddd; }\n',
    ])
  stylesheet.dump()  
  print stylesheet.lookup(None, ['p'])
  print stylesheet.lookup(None, ['ul'])
  print stylesheet.lookup(None, ['li'], (set(), set(['','/ul'])))
  p = Style(color=[u'white'], top=[(40,'')])
  print stylesheet.lookup(p, ['p'])
  print stylesheet.lookup(p, ['ul'])
  print stylesheet.lookup(p, ['li'], (set(), set(['','/ul'])))
  print stylesheet.lookup(p, ['li'], (set(['','/ul']), set(['foo'])))
  s1 = Style(width=[(10,'')])
  print s1
  s2 = Style(width=[(50,'em')])
  print s2
  
if __name__ == '__main__': read_stylesheet()
