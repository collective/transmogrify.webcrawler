#!/usr/bin/env python
import sys, os

def main(args):
  if not args:
    for dir in sys.stdin:
      dir = dir.strip()
      for fname in os.listdir(dir):
        if fname.endswith('.txt'):
          args.append('%s/%s' % (dir,fname))
  def percent(x,y):
    if y:
      return '(%3d%%)' % (100*x/y)
    else:
      return ' ---- '
  totaldocs = 0
  totalcorrect = 0
  dic = {}
  for fname in args:
    k = os.path.basename(fname)
    k = k[:k.index('.')]
    (ndocs1,correct1) = (0,0)
    (ndocs,correct,_x,_y) = dic.get(k, (0,0,0,0))
    fp = file(fname)
    body = title = False
    for line in fp:
      line = line.strip()
      if line.startswith('!'):
        ndocs1 += 1
        if body and title:
          correct1 += 1
        body = title = False
      elif line.startswith('MAIN-'):
        body = True
      elif line.startswith('TITLE:'):
        title = True
    if body and title:
      correct1 += 1
    fp.close()
    dic[k] = (ndocs+ndocs1,correct+correct1,ndocs1,correct1)
  for k in sorted(dic.keys()):
    (ndocs,correct,ndocs1,correct1) = dic[k]
    print '%20s: %4d/ %4d %s %4d/ %4d %s' % (k, correct, ndocs, percent(correct,ndocs),
                                           correct1, ndocs1, percent(correct1,ndocs1))
    totaldocs += ndocs
    totalcorrect += correct
  if totaldocs:
    print '-'*60
    print '%20s:%5d/%5d %s' % ('TOTAL', totalcorrect,totaldocs, percent(totalcorrect,totaldocs))
  return

if __name__ == "__main__": main(sys.argv[1:])
