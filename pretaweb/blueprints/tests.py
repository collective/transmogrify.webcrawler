
import unittest

from zope.testing import doctest
from zope.component import provideUtility
from Products.Five import zcml
from zope.component import provideUtility
from zope.interface import classProvides, implements
from collective.transmogrifier.interfaces import ISectionBlueprint, ISection

from collective.transmogrifier.tests import setUp as baseSetUp
from collective.transmogrifier.tests import tearDown
from collective.transmogrifier.sections.tests import PrettyPrinter

from pretaweb.blueprints.webcrawler import WebCrawler
from pretaweb.blueprints.treeserializer import TreeSerializer
from pretaweb.blueprints.typerecognitor import TypeRecognitor
from pretaweb.blueprints.safeportaltransforms import  SafePortalTransforms
from templatefinder import TemplateFinder
from pretaweb.blueprints.relinker import Relinker
from pretaweb.blueprints.simplexpath import SimpleXPath
from plone.i18n.normalizer import urlnormalizer

class HTMLSource(object):
    classProvides(ISectionBlueprint)
    implements(ISection)
    
    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        def item(path, text):
            i = dict(_mimetype="text/html",_site_url="http://test.com/")
            i.update(dict(_path=key,text=value,_mimetype="text/html"))
            return i
        self.items = [item(key,value) for key,value in options.items() if key!='blueprint']
        
    def __iter__(self):
        for item in self.previous:
            yield item
            
        for item in self.items:
            yield item



def setUp(test):
    baseSetUp(test)
        
    from collective.transmogrifier.transmogrifier import Transmogrifier
    test.globs['transmogrifier'] = Transmogrifier(test.globs['plone'])
    
    import zope.component
    import collective.transmogrifier.sections
    zcml.load_config('meta.zcml', zope.app.component)
    zcml.load_config('configure.zcml', collective.transmogrifier.sections)
    
    provideUtility(PrettyPrinter,
        name=u'collective.transmogrifier.sections.tests.pprinter')
    provideUtility(WebCrawler,
        name=u'pretaweb.blueprints.webcrawler')
    provideUtility(TreeSerializer,
        name=u'pretaweb.blueprints.treeserializer')
    provideUtility(TypeRecognitor,
        name=u'pretaweb.blueprints.typerecognitor')
    provideUtility(TemplateFinder,
        name=u'pretaweb.blueprints.templatefinder')
    provideUtility(urlnormalizer)
    provideUtility(Relinker,
        name=u'pretaweb.blueprints.relinker')
    provideUtility(SimpleXPath,
        name=u'pretaweb.blueprints.simplexpath')
    provideUtility(SafePortalTransforms,
        name=u'pretaweb.blueprints.safeportaltransforms')
    from backlinkstitle import BacklinksTitle
    provideUtility(BacklinksTitle,
        name=u'pretaweb.blueprints.backlinkstitle')
    from isindex import IsIndex
    provideUtility(IsIndex,
        name=u'pretaweb.blueprints.isindex')
    from pathmover import PathMover
    provideUtility(PathMover,
        name=u'pretaweb.blueprints.pathmover')
    from safeatschemaupdater import SafeATSchemaUpdaterSection
    provideUtility(SafeATSchemaUpdaterSection,
        name=u'pretaweb.blueprints.safeatschemaupdater')

    provideUtility(HTMLSource,
        name=u'pretaweb.blueprints.test.htmlsource')


def test_suite():
    return unittest.TestSuite((
        doctest.DocFileSuite('webcrawler.txt', setUp=setUp, tearDown=tearDown),
        doctest.DocFileSuite('treeserializer.txt', setUp=setUp, tearDown=tearDown),
        doctest.DocFileSuite('typerecognitor.txt', setUp=setUp, tearDown=tearDown),
        doctest.DocFileSuite('templatefinder.txt', setUp=setUp, tearDown=tearDown),
        doctest.DocFileSuite('relinker.txt', setUp=setUp, tearDown=tearDown),
        doctest.DocFileSuite('pathmover.txt', setUp=setUp, tearDown=tearDown),
        doctest.DocFileSuite('simplexpath.txt', setUp=setUp, tearDown=tearDown),
        #doctest.DocTestSuite('pretaweb.blueprints.templatefinder', setUp=setUp, tearDown=tearDown),

    ))

