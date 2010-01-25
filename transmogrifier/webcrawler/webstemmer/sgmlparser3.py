#!/usr/bin/env python
#
# sgmlparser3.py
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

import re
from htmlentitydefs import name2codepoint

__all__ = [ 'SGMLParser3' ]

COMMENT_MAXMINUSES = 1000
DECLSTR_MAXCHARS = 1000 # maxchars for decl tag.
NOT_ATTRVALUE0 = re.compile(r'[\s><&]')
NOT_ATTRVALUE_DQ = re.compile(r'[&\"]')
NOT_ATTRVALUE_SQ = re.compile(r'[&\']')
ATTRVALUE_MAXCHARS = 4000
SPECIAL_CHAR0 = re.compile(r'[&<]')
ATTRVALUE_SOMETHING = re.compile(r'[^\s]')
NOT_TAGNAME = re.compile(r'[\s<>/\?!=\"\']')
TAGNAME_MAXCHARS = 30 # maxchars for tag name or attr name.
NOT_ENTITY_NAME = re.compile(r'[^a-zA-Z0-9#]')
ENTITY_NAME_MAXCHARS = 20
TAGNAME_SOMETHING = re.compile(r'[^\s]')


##  SGMLParser3
##
class SGMLParser3:
  """
  Robust feed based SGML parser.
  Mainly for instantiating HTMLParser3.
  """

  def __init__(self):
    # parse1: current state:
    #   parse_pcdata, parse_cdata, parse_cdata_end, 
    #   parse_entity_0, parse_entity_1,
    #   parse_tag_0, parse_tag_1, parse_tag_attr_0, parse_tag_attr_1,
    #   parse_tag_attrvalue_0, parse_tag_attrvalue_1,
    #   parse_decl, parse_comment_0, parse_comment_1, parse_comment_2,
    self.parse1 = self.parse_pcdata
    # parse0: previous state
    self.parse0 = None
    self.charpos = 0
    return

  def close(self):
    """Finish parsing and discard all uncomplete tags and entities."""
    return

  # You should inherit the following methods.

  def handle_start_tag(self, name, attrs):
    raise NotImplementedError
  
  def handle_end_tag(self, name, attrs):
    raise NotImplementedError
  
  def handle_decl(self, name):
    raise NotImplementedError
  
  def handle_directive(self, name, attrs):
    raise NotImplementedError
  
  def handle_characters(self, data):
    raise NotImplementedError

  # Internal methods.

  def handle_entity(self, name0):
    """Convert an HTML entity name to one or more unicode character(s).

    Generally, you shouldn't change this method, as this is called
    from other internal methods.
    """
    name = name0.lower()
    if name in name2codepoint:
      # entityref
      return unichr(name2codepoint[name])
    else:
      # charref
      if name.startswith('#x'):
        try:
          return unichr( int(name[2:], 16) )
        except ValueError: # not a hex number, or not valid unichr number.
          pass
      elif name.startswith('#'):
        try:
          return unichr( int(name[1:]) )
        except ValueError: # not a int number, or not valid unichr number.
          pass
      return u'&'+name0

  def feed(self, x):
    """Feed a unicode string to the parser.

    This parser tries to decide things as quickly as possible,
    generally all complete tags and entities included in a string
    are immediately interpreted and proper action is taken.
    """
    i = 0
    assert isinstance(x, unicode)
    while 0 <= i and i < len(x):
      i = self.parse1(x, i)
    return self
  feed_unicode = feed

  def parse_pcdata(self, x, i0):
    m = SPECIAL_CHAR0.search(x, i0)
    self.charpos = i0
    if not m:
      assert i0 < len(x)
      self.handle_characters(x[i0:])
      return -1
    # special character found
    i1 = m.start(0)
    if i0 < i1:
      self.handle_characters(x[i0:i1])
    c = x[i1]
    if c == '&':                      # meet: '&'
      self.feed_entity = self.handle_characters
      self.parse0 = self.parse_pcdata
      self.parse1 = self.parse_entity_0
    else:                             # meet: '<'
      self.parse1 = self.parse_tag_0
    self.charpos = i1
    return i1

  # this is called manually by a subclass
  def start_cdata(self, endname):
    self.cdata_endstr = '</'+endname
    self.parse1 = self.parse_cdata
    return

  def parse_cdata(self, x, i0):
    i1 = x.find('<', i0)
    if i1 == -1:
      assert i0 < len(x)
      self.handle_characters(x[i0:])
      return -1
    if i0 < i1:
      self.handle_characters(x[i0:i1])
    self.cdata_endcheck = '<'
    self.parse1 = self.parse_cdata_end
    return i1+1
    
  def parse_cdata_end(self, x, i0):
    need = len(self.cdata_endstr) - len(self.cdata_endcheck)
    assert 0 < need
    left = len(x) - i0
    if left < need:
      self.cdata_endcheck += x[i0:]
      return -1
    i1 = i0+need
    self.cdata_endcheck += x[i0:i1]
    # now sufficient chars are available, check it.
    if self.cdata_endcheck.lower() == self.cdata_endstr:
      assert self.cdata_endstr.startswith('</')
      # ending tag
      self.cdata_endstr = ''
      self.attr_name = self.cdata_endstr[2:]
      self.handle_tag = self.handle_end_tag
      self.parse1 = self.parse_tag_attr_0
    else:
      # cdata still continues...
      # partial scan (for handling nasty "</scr</script>" case)
      i = self.cdata_endcheck.find('<', 1)
      if i == -1:
        self.handle_characters(self.cdata_endcheck)
        self.parse1 = self.parse_cdata
      else:
        self.handle_characters(self.cdata_endcheck[:i])
        self.cdata_endcheck = self.cdata_endcheck[i:]
    return i1

  # Parse entityrefs.
  
  def parse_entity_0(self, x, i0):
    assert x[i0] == '&'
    self.parse1 = self.parse_entity_1
    self.entity_name = ''
    return i0+1
  
  def parse_entity_1(self, x, i0):
    m = NOT_ENTITY_NAME.search(x, i0)
    if not m:
      if len(self.entity_name) < ENTITY_NAME_MAXCHARS:
        self.entity_name += x[i0:]
      return -1        
    # end of entity name
    i1 = m.start(0)
    if len(self.entity_name) < ENTITY_NAME_MAXCHARS:
      self.entity_name += x[i0:i1]
    self.feed_entity(self.handle_entity(self.entity_name))
    # "return" to the previous state.
    self.parse1 = self.parse0
    c = x[i1]
    if c == ';':
      i1 += 1
    return i1
    
  # Parse start/end tags.
  
  def parse_tag_0(self, x, i0):
    assert x[i0] == '<'
    self.parse1 = self.parse_tag_1
    self.tag_name = ''
    self.tag_attrs = []
    return i0+1

  def parse_tag_1(self, x, i0):
    c = x[i0]
    if c == '!':
      self.decl_string = ''
      self.parse1 = self.parse_decl
      i0 += 1
    elif c == '?':
      self.attr_name = ''
      self.handle_tag = self.handle_directive
      self.parse1 = self.parse_tag_attr_0
      i0 += 1
    elif c == '/':
      self.attr_name = ''
      self.handle_tag = self.handle_end_tag
      self.parse1 = self.parse_tag_attr_0
      i0 += 1
    else:
      self.attr_name = ''
      self.handle_tag = self.handle_start_tag
      self.parse1 = self.parse_tag_attr_0
    return i0

  # Parse tag attributes.
  
  def parse_tag_attr_0(self, x, i0):
    # looking for a tagname/attrvalue...
    m = TAGNAME_SOMETHING.search(x, i0)
    if not m:
      # ignore intermediate characters.
      return -1
    i1 = m.start(0)
    c = x[i1]
    if c == '=':
      # attr value starting...
      self.parse1 = self.parse_tag_attrvalue_0
      return i1+1
    # tagname/attrname/endoftag found...
    if self.attr_name:
      # fix attr if any.
      self.tag_attrs.append((self.attr_name, self.attr_name))
    self.attr_name = ''
    if c == '<':
      # meet: '<...<'
      self.parse1 = self.parse_tag_0
      self.handle_tag(self.tag_name, self.tag_attrs) # this may change self.parse1 (CDATA).
    elif c == '>':
      # meet: '<...>'
      self.parse1 = self.parse_pcdata
      self.handle_tag(self.tag_name, self.tag_attrs) # this may change self.parse1 (CDATA).
      # eat this character.
      i1 += 1
    else:
      if c in '/?!\"\'':
        i1 += 1
      # attrname starting...
      self.parse1 = self.parse_tag_attr_1
    return i1
  
  def parse_tag_attr_1(self, x, i0):
    # eating characters for a name...
    m = NOT_TAGNAME.search(x, i0)
    if not m:
      if len(self.attr_name) < TAGNAME_MAXCHARS:
        self.attr_name += x[i0:]
      return -1
    # tagname/attrname now complete, what's next?
    i1 = m.start(0)
    if len(self.attr_name) < TAGNAME_MAXCHARS:
      self.attr_name += x[i0:i1]
    self.attr_name = self.attr_name.lower()
    if not self.tag_name:
      self.tag_name = self.attr_name
      self.attr_name = ''
    self.parse1 = self.parse_tag_attr_0
    return i1

  def parse_tag_attrvalue_0(self, x, i0):
    # looking for an attrvalue...
    m = ATTRVALUE_SOMETHING.search(x, i0)
    if not m:
      return -1
    i1 = m.start(0)
    c = x[i1]
    self.attr_value = ''
    if c == '<' or c == '>':
      # value end
      self.parse1 = self.parse_tag_attr_0
    elif c == '"':
      self.not_attrvalue = NOT_ATTRVALUE_DQ
      self.parse1 = self.parse_tag_attrvalue_1
      i1 += 1
    elif c == "'":
      self.not_attrvalue = NOT_ATTRVALUE_SQ
      self.parse1 = self.parse_tag_attrvalue_1
      i1 += 1
    else:
      self.not_attrvalue = NOT_ATTRVALUE0
      self.parse1 = self.parse_tag_attrvalue_1
    return i1

  def parse_tag_attrvalue_addentity(self, c):
    self.attr_value += c
    return
  def parse_tag_attrvalue_1(self, x, i0):
    # eating characters for a value...
    m = self.not_attrvalue.search(x, i0)
    if not m:
      if len(self.attr_value) < ATTRVALUE_MAXCHARS:
        assert i0 < len(x)
        self.attr_value += x[i0:]
      return -1
    i1 = m.start(0)
    if len(self.attr_value) < ATTRVALUE_MAXCHARS:
      self.attr_value += x[i0:i1]
    c = x[i1]
    if c == '&':
      # "call" the entityref parser.
      self.feed_entity = self.parse_tag_attrvalue_addentity
      self.parse0 = self.parse_tag_attrvalue_1
      self.parse1 = self.parse_entity_0
      return i1
    # end of value.
    if self.attr_name:
      self.tag_attrs.append((self.attr_name, self.attr_value))
      self.attr_name = ''
    self.parse1 = self.parse_tag_attr_0
    if c == "'" or c == '"':
      i1 += 1
    return i1

  # Parse SGML declarations or comments.
  def parse_decl(self, x, i0):
    if x[i0] == '-':
      self.parse1 = self.parse_comment_0
      return i0+1
    i1 = x.find('>', i0)
    if i1 == -1:
      if len(self.decl_string) < DECLSTR_MAXCHARS:
        self.decl_string += x[i0:]
    else:
      if len(self.decl_string) < DECLSTR_MAXCHARS:
        self.decl_string += x[i0:i1]
      self.handle_decl(self.decl_string)
      self.parse1 = self.parse_pcdata
      i1 += 1
    return i1

  # beginning '-'
  def parse_comment_0(self, x, i0):
    if x[i0] == '-':
      return i0+1
    elif x[i0] == '>':
      self.parse1 = self.parse_comment_2
    else:
      self.handle_start_tag('comment', {})
      self.parse1 = self.parse_comment_1
    return i0
  
  def parse_comment_1(self, x, i0):
    i1 = x.find('-', i0)
    if i1 == -1:
      assert i0 < len(x)
      self.handle_characters(x[i0:])
    else:
      if i0 < i1:
        self.handle_characters(x[i0:i1])
      self.parse1 = self.parse_comment_2
      self.comment_minuses = 1
      i1 += 1
    return i1
  
  # trailing '-'
  def parse_comment_2(self, x, i0):
    c = x[i0]
    if c == '>':
      self.handle_end_tag('comment', {})
      self.parse1 = self.parse_pcdata
      return i0+1
    elif c == '-':
      self.comment_minuses += 1
      return i0+1
    self.handle_characters(u'-' * min(self.comment_minuses, COMMENT_MAXMINUSES))
    self.parse1 = self.parse_comment_1
    return i0
