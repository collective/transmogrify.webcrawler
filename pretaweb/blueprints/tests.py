
import unittest

from zope.testing import doctest
from zope.component import provideUtility
from Products.Five import zcml

from collective.transmogrifier.tests import setUp as baseSetUp
from collective.transmogrifier.tests import tearDown
from collective.transmogrifier.sections.tests import PrettyPrinter

from pretaweb.blueprints.webcrawler import WebCrawler
from pretaweb.blueprints.treeserializer import TreeSerializer
from pretaweb.blueprints.typerecognitor import TypeRecognitor
from pretaweb.blueprints.relinker import Relinker
from plone.i18n.normalizer import urlnormalizer


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
    provideUtility(urlnormalizer)
    provideUtility(Relinker,
        name=u'pretaweb.blueprints.relinker')


def test_suite():
    return unittest.TestSuite((
        doctest.DocFileSuite('webcrawler.txt', setUp=setUp, tearDown=tearDown),
        doctest.DocFileSuite('treeserializer.txt', setUp=setUp, tearDown=tearDown),
        doctest.DocFileSuite('typerecognitor.txt', setUp=setUp, tearDown=tearDown),
        doctest.DocFileSuite('relinker.txt', setUp=setUp, tearDown=tearDown),
    ))



