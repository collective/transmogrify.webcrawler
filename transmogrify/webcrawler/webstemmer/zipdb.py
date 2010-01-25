#!/usr/bin/env python
#
# zipdb.py
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
from zipfile import ZipFile, ZIP_DEFLATED
stderr = sys.stderr


##  ACLDB
##
class ACLDB:
  
  def __init__(self):
    self.pats = []
    return
  
  def add_allow(self, pat):
    self.pats.append( (True, re.compile(pat)) )
    return
  
  def add_deny(self, pat):
    self.pats.append( (False, re.compile(pat)) )
    return
  
  def allowed(self, url):
    for (f,p) in self.pats:
      if p.search(url): break
    else:
      return False
    return f


##  ZipDumper
##
class Dumper:
  def feed_page(self, name, data):
    return
  def close(self):
    return

NullDumper = Dumper
  
class ZipDumper(Dumper):
  
  def __init__(self, fname, baseid):
    zipname = '%s.%s.zip' % (fname,baseid)
    print >>stderr, 'Writing: %r' % zipname
    self.fp = ZipFile(zipname, 'w', ZIP_DEFLATED)
    return
  
  def feed_page(self, name, data):
    self.fp.writestr(name, data)
    return
  
  def close(self):
    self.fp.close()
    return


##  ZipLoader
##
class ZipLoader:
  
  def __init__(self, consumer, fname, acldb=None, debug=0):
    self.consumer = consumer
    self.debug = debug
    self.fname = fname
    self.acldb = acldb
    return
  
  def run(self):
    fp = ZipFile(self.fname, 'r')
    print >>stderr, 'Opening: %r...' % self.fname
    for name in fp.namelist():
      if not self.acldb or self.acldb.allowed(name):
        if self.debug:
          print >>stderr, 'Load: %s' % name
        if self.consumer:
          self.consumer.feed_page(name, fp.read(name))
    fp.close()
    return
