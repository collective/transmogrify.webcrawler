#!/usr/bin/env python
#
# urldbutils.py
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

import sys, time, struct, os
stderr = sys.stderr

from bsddb import hashopen as dbmopen

# reorganize db
def reorgdb(outname, fname, threshold, verbose):
  print >>stderr, 'input=%s, output=%s, threshold=%d' % (fname, outname, threshold)
  try:
    os.stat(outname)
    raise IOError('file %r already exists.' % outname)
  except OSError:
    pass
  now = int(time.time())
  db = dbmopen(fname, 'r')
  out = dbmopen(outname, 'c')
  remain = 0
  filtered = 0
  for (k,v) in db.iteritems():
    t = struct.unpack('<L', v)[0]
    if now-t < threshold:
      out[k] = v
      remain += 1
    else:
      filtered += 1
      if verbose:
        print ''.join([ '%02x' % ord(c) for c in k ]), time.asctime(time.localtime(t)), '(out)'
  print >>stderr, 'total: %d (remain: %d, filtered: %d)' % (remain+filtered, remain, filtered)
  db.close()
  out.close()
  return

# display db
def dispdb(fname, threshold, verbose):
  now = int(time.time())
  db = dbmopen(fname, 'r')
  for (k,v) in db.iteritems():
    t = struct.unpack('<L', v)[0]
    print ''.join([ '%02x' % ord(c) for c in k ]), time.asctime(time.localtime(t)),
    if threshold <= now-t:
      print '(out)'
    else:
      print '(in)'
  db.close()
  return

# main
if __name__ == "__main__":
  import getopt
  def usage():
    print "usage: urldbutils.py [-v)erbose] {-D)ump|-R)eorganize} [-t days] urldb [urldb.old]"
    sys.exit(2)
  try:
    (opts, args) = getopt.getopt(sys.argv[1:], "vDRt:")
  except getopt.GetoptError:
    usage()
  (mode, threshold, verbose) = (1, 0, False)
  for (k, v) in opts:
    if k == "-v": verbose = True
    elif k == "-D": mode = 1
    elif k == "-R": mode = 2
    elif k == "-t": threshold = int(v)*86400
  if not mode or not args:
    usage()
  if not threshold:
    print >>sys.stderr, 'please specify threshold.'
    usage()
  if mode == 1:
    dispdb(args[0], threshold, verbose)
  elif mode == 2:
    if len(args) < 2:
      usage()
    reorgdb(args[0], args[1], threshold, verbose)
