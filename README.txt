Crawling - html to import
=========================
A source blueprint for crawling content from a site or local html files.

Webcrawler imports HTML either from a live website, for a folder on disk, or a folder
on disk with html which used to come from a live website and may still have absolute
links refering to that website.

To crawl a live website supply the crawler with a base http url to start crawling with.
This url must be the url which all the other urls you want from the site start with.

For example ::

 [crawler]
 blueprint = transmogrify.webcrawler
 url  = http://www.whitehouse.gov
 max = 50

will restrict the crawler to the first 50 pages.

You can also crawl a local directory of html with relative links by just using a file: style url ::

 [crawler]
 blueprint = transmogrify.webcrawler
 url = file:///mydirectory
 
or if the local directory contains html saved from a website and might have absolute urls in it
the you can set this as the cache. The crawler will always look up the cache first ::

 [crawler]
 blueprint = transmogrify.webcrawler
 url = http://therealsite.com --crawler:cache=mydirectory

The following will not crawl anything larget than 4Mb ::

  [crawler]
  blueprint = transmogrify.webcrawler
  url  = http://www.whitehouse.gov
  maxsize=400000

To skip crawling links by regular expression ::
 
  [crawler]
  blueprint = transmogrify.webcrawler
  url=http://www.whitehouse.gov
  ignore = \.mp3
                   \.mp4 

If webcrawler is having trouble parsing the html of some pages you can preprocesses
the html before it is parsed. e.g. ::

  [crawler]
  blueprint = transmogrify.webcrawler
  patterns = (<script>)[^<]*(</script>)
  subs = \1\2
  
If you'd like to skip processing links with certain mimetypes you can use the
drop:condition. This TALES expression determines what will be processed further.
see http://pypi.python.org/pypi/collective.transmogrifier/#condition-section
::

 [drop]
 blueprint = collective.transmogrifier.sections.condition
 condition: python:item.get('_mimetype') not in ['application/x-javascript','text/css','text/plain','application/x-java-byte-code'] and item.get('_path','').split('.')[-1] not in ['class']


Options
-------

site_url
 - the top url to crawl

ignore
 - list of regex for urls to not crawl

cache
 - local directory to read crawled items from instead of accessing the site directly

patterns
 - Regular expressions to substitute before html is parsed. New line seperated

subs
 - Text to replace each item in patterns. Must be the same number of lines as patterns.  Due to the way buildout handles empty lines, to replace a pattern with nothing (eg to remove the pattern), use ``<EMPTYSTRING>`` as a substitution.

maxsize
 - don't crawl anything larger than this

max
 - Limit crawling to this number of pages

start-urls
 - a list of urls to initially crawl

ignore-robots
 - if set, will ignore the robots.txt directives and crawl everything
  
WebCrawler will emit items like ::

 item = dict(_site_url = "Original site_url used",
            _path = "The url crawled without _site_url,
            _content = "The raw content returned by the url",
            _content_info = "Headers returned with content"
            _backlinks    = names,
            _sortorder    = "An integer representing the order the url was found within the page/site
	     )
  

transmogrify.webcrawler.typerecognitor
======================================

A blueprint for assinging content type based on the mime-type as given by the
webcrawler

transmogrify.webcrawler.cache
=============================

A blueprint that saves crawled content into a directory structure

