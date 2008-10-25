#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
#
# Create a relative URL given to absolute URLs
# See tests at the end:
# test_relative_url("http://foo/a/b", "http://foo/c", "../c")
#
# (c) May 2002 Thomas Guettler http://www.thomas-guettler.de
# This code is in the public domain
# Feedback Welcome
#

import urlparse
import re
import string


def relative_url(source, target):
    su=urlparse.urlparse(source)
    tu=urlparse.urlparse(target)
    junk=tu[3:]
    if su[0]!=tu[0] or su[1]!=tu[1]:
        #scheme (http) or netloc (www.heise.de) are different
        #return absolut path of target
        return target
    su=re.split("/", su[2])
    tu=re.split("/", tu[2])
    su.reverse()
    tu.reverse()

    #remove parts which are equal   (['a', 'b'] ['a', 'c'] --> ['c'])
    while len(su)>0 and len(tu)>0 and su[-1]==tu[-1]:
        su.pop()
        last_pop=tu.pop()
    if len(su)==0 and len(tu)==0:
        #Special case: link to itself (http://foo/a http://foo/a -> a)
        tu.append(last_pop)
    if len(su)==1 and su[0]=="" and len(tu)==0:
        #Special case: (http://foo/a/ http://foo/a -> ../a)
        su.append(last_pop)
        tu.append(last_pop)
    tu.reverse()
    relative_url=[]
    for i in range(len(su)-1): 
        relative_url.append("..")
    rel_url=string.join(relative_url + tu, "/")
    rel_url=urlparse.urlunparse(["", "", rel_url, junk[0], junk[1], junk[2]])
    return rel_url

def test_relative_url(source, target, result):
    res=relative_url(source, target)
    if res!=result:
        print "Test FAILED: result is:", res, "should be:", result, \
              "source:", source, "target:", target
    else:
        print "Test ok: result is:", res, "source:", source, "target:", target
        
if __name__ == "__main__":
    test_relative_url("http://foo/a/b", "http://foo/c", "../c")
    test_relative_url("http://foo/a/b", "http://foo/c/d", "../c/d")
    test_relative_url("http://foo/a/b", "ftp://foo/c", "ftp://foo/c")
    test_relative_url("http://foo/a", "http://foo/b", "b")
    test_relative_url("http://foo/a/", "http://foo/b", "../b")
    test_relative_url("http://foo:80/a/", "http://foo/b", "http://foo/b")
    test_relative_url("http://foo:8080/a/", "http://foo/b", "http://foo/b")
    test_relative_url("http://foo/a", "http://foo/a", "a")
    test_relative_url("http://foo/a/", "http://foo/a", "../a")
    test_relative_url("http://foo/a", "http://foo/b/c", "b/c")
    test_relative_url("http://foo/a/", "http://foo/b/c", "../b/c")
    test_relative_url("http://foo/a/b", "http://foo/c/d", "../c/d")
    test_relative_url("http://foo/a/b/", "http://foo/c/d", "../../c/d")
    test_relative_url("http://foo/a", "http://foo/b", "b")
    test_relative_url("http://foo/a;para?query#frag", "http://foo/a", "a")
    test_relative_url("http://foo/a", "http://foo/a;para?query#frag",
                      "a;para?query#frag")
    test_relative_url("a/b", "a/c", "c")
