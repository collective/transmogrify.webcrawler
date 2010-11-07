Introduction
============

transmogrify.webcrawler
  A source blueprint for crawling content from a site or local html files.
  
# WebCrawler will emit items like
# item = dict(_site_url = "Original site_url used",
#            _path = "The url crawled without _site_url,
#            _content = "The raw content returned by the url",
#            _content_info = "Headers returned with content"
#            _backlinks    = names,
#            _sortorder    = "An integer representing the order the url was found within the page/site
#	     )
  

transmogrify.webcrawler.typerecognitor
  A blueprint for assinging content type based on the mime-type as given by the
  webcrawler

transmogrify.webcrawler.cache
  A blueprint that saves crawled content into a directory structure

