
Funnelweb is built using transmogrifier to allow importing of static html websites into plone.

Getting started
---------------

Once installed any folderish object in Plone will have a "Import from website" dropdown action item 
as long as you have rights to add content within that folder.

  >>> browser = self.browser
  
  >>> browser.getLink('Import from website...')
  <Link text='Import from website...' url='http://nohost/plone/@@funnelwebimport'>
  
  >>> browser.getLink('Import from website...').click()

This will allow say how you want your site imported.
The dialog is layed out according to various steps in the transformation process

  >>> print browser.contents
  <BLANKLINE>
  ...
  ...Webcrawler...
  ...
  ...Template Analyser...
  ...
  ...Index Analyser...
  ...
  ...Document Conversion...
  ...
  ...Attachment Analyser...
  ...
  ...Title Analyser...
  ...
  ...Content Importer...
  ...

Webcrawler
----------
  
Webcrawler is what go and collects the web pages from the external site.
The only compulsory field is the URL of the site to import

  >>> self.testsite
  'file:///.../test_staticsite'
  
  >>> browser.getControl('Import URL').value = self.testsite

The crawler will only crawler the site with urls that begin with this url.
In addition it will ignore urls which match additional patterns you enter
  
  >>> print browser.getControl('URLs to ignore').value
  cgi-bin
  javascript:

The crawler will also ignore certain mimetype if you don't wish to import these

  >>> print browser.getControl('Mimetypes to ignore').value
  application/x-javascript
  text/css
  application/x-java-byte-code  

Content Extractor
-----------------

Content Extractor performs an analysis on all the pages collected. It will determine what is unique 
content on each page and extract it. If the analysis fails you can override it with an XPath expressions.

  >>> browser.getControl('Title XPath').value
  ''
  >>> browser.getControl('Description XPath').value
  ''
  >>> browser.getControl('Body XPath').value
  ''

Index Analyser
--------------
  
Index Analyser will try to determine which content should the default content for a folder view.

#  >>> browser.getControl('Enable Index Analyser').value
#  True

Document Conversion
-------------------
 
Document Conversion will attempt to convert certain non HTML content into HTML so they appear 
as Pages in Plone.

#  >>> browser.getControl('Mimetypes to convert').displayValues
#  ['Word Document', 'PDF Document']

Attachment Analyser
-------------------
  
Attachment analyser will find images and pages which are only linked from one location and move them
into the same location.

#  >>> browser.getControl('Enable Attachment Analyser').value
#  True

Title Analyser
--------------

Title Analyser looks for better titles for content by using anchor text

#  >>> browser.getControl('Enable Title Analyser').value
#  True

Content Importer
----------------
  
Content Importer will construct new content or overwrite existing content in the current folder.

#  >>> browser.getControl('Enable Construct Content').value
#  True
  
#  >>> browser.getControl('Overwrite existing content').value
#  True

Plone tracks content that has been renamed or moved. Content Importer can use that information 
so that a second import will find the moved content and overwrite it.
  
#  >>> browser.getControl('Overwrite moved content').value
#  True

Once created we also have the option of changing the state of the newly created content  

#  >>> browser.getControl('Set State for imported content').displayOptions
#  ['No Change','Published','Review','Private']
#  >>> browser.getControl('Set State for imported content').value
#  Published
  
Running Website importer  
------------------------
  
If we start the import

  >>> browser.getControl('Start Import').click()
  
the progress of the import will be shown as totals of items imported into each 
step until all webcrawled items have been processed.

  >>> print browser.contents
  <BLANKLINE>
  ...10 Items successfully imported... 
  ...(12)...Webcrawler
  ...
  ...(10)...Filter Mimetypes
  ...
  ...(10)...Content Extractor
  ...
  ...(10)...Index Analyser
  ...
  ...(10)...Document Conversion
  ...
  ...(10)...Attachment Analyser
  ...
  ...(10)...Titles from Link
  ...
  ...(10)...Construct Content
  ...
  ...(10)...Publish Content
  ...
      
  


Overview
========

Intranets and public websites often start out as static html sites built using a simple template, 
or in a basic CMS. Often the first step in switching to plone is import this content so it can be 
restructured and managed within Plone. In the past this has been done by bulk uploading via webdav 
or ftp and then manually fixing the html for each page, or via homegrown scripts. FunnelWeb will 
instead take a site, analsye its structure, content and links and attempt to import just the content 
in a well structured, well linked way so minimal effort needs to go into further restructuring.
About the name

Goals
=====

    * Import folder action that takes a single url
    * webcrawler capable of reading html from a live site or filesystem html
    * detemplater capable of automatically detecting content from repeated html template code. With manual xpath override.
    * structural analysis resulting in combinging, seperating, renaming or moving content so looks nicer in plone.
    * ability to convert word and other propriatory formats to html automatically
    * relinking so the content is fully linked after import
    * built on top of transmogrifier to leverage existing import code

What is out of scope currently is reimporting or synchronising content and extracting more than just Pages and Images.
Planning

   1. Get an initial version into alpha testing
   2. Test on a variety of sites including those built on common CMS systems as well as custom html.
   3. Improve detemplating and restructuring heuristics to work on as many sites as possible.

How you can help
================

At this stage just join this project to be a part of the alpha testing 

About the name
==============

The Sydney Funnel Web Spider is the most deadly spider in the world able to kill a child in less than 
2 hours. Sydney Funnel web spiders are native to Sydney, Australia, which also happens to be the home 
of the company that founded this project, the Plone specialist web solutions company Pretaweb. 
Since the project also involved spiders, crawling, and funneling the web through a process to reduce 
it down, it seemed apt.
