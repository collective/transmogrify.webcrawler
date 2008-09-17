
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
from collective.transmogrifier.sections.tests import SampleSource

from pretaweb.blueprints.webcrawler import WebCrawler
from pretaweb.blueprints.treeserializer import TreeSerializer
from pretaweb.blueprints.typerecognitor import TypeRecognitor
from pretaweb.blueprints.safeportaltransforms import  SafePortalTransforms
from pretaweb.blueprints.makeattachments import MakeAttachments
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
    from constructor import SafeConstructorSection
    provideUtility(SafeConstructorSection,
        name=u'pretaweb.blueprints.constructor')
    from makeattachments import MakeAttachments
    provideUtility(MakeAttachments,
        name=u'pretaweb.blueprints.makeattachments')

    provideUtility(HTMLSource,
        name=u'pretaweb.blueprints.test.htmlsource')


def SafeATSchemaUpdaterSetUp(test):
    setUp(test)

    from Products.Archetypes.interfaces import IBaseObject
    class MockPortal(object):
        implements(IBaseObject)
        
        def unrestrictedTraverse(self, path, default):
            return self

        _file_value = None
        _file_filename = None
        _file_mimetype = None
        _file_field = None

        def set(self, name, value, **arguments):
            self._file_field = name
            self._file_value = value
            if 'mimetype' in arguments:
                self._file_mimetype = arguments['mimetype']
            if 'filename' in arguments:
                self._file_filename = arguments['filename']

        def get(self, name):
            return self._file_value
        
        def checkCreationFlag(self):
            pass

        def unmarkCreationFlag(self):
            pass

        def getField(self, name):
            return self

    test.globs['plone'] = MockPortal()
    test.globs['transmogrifier'].context = test.globs['plone']

    class SafeATSchemaUpdaterSectionSource(SampleSource):
        classProvides(ISectionBlueprint)
        implements(ISection)

        def __init__(self, *args, **kw):
            super(SafeATSchemaUpdaterSectionSource, self).__init__(*args, **kw)
            self.sample = (
                {'_path': '/dummy',
                 'file': 'image content',
                 'file.filename': 'image.jpg',
                 'file.mimetype': 'image/jpeg',},
            )
    provideUtility(SafeATSchemaUpdaterSectionSource,
        name=u'pretaweb.blueprints.tests.safeatschemaupdatersource')

def MakeAttachmentsSetUp(test):
    setUp(test)

    class MakeAttachmentsSource(SampleSource):
        classProvides(ISectionBlueprint)
        implements(ISection)

        def __init__(self, *args, **kw):
            super(MakeAttachmentsSource, self).__init__(*args, **kw)
            self.sample = (
                {'_site_url': 'http://www.test.com',
                 '_path': '/item1',},
                {'_site_url': 'http://www.test.com',
                 '_path': '/subitem1',
                 '_backlinks': {'http://www.test.com/item1': ''},
                 'title': 'subitem1 title',
                 'decription': 'test if condition is working',
                 '_type': 'Document'},
                {'_site_url': 'http://www.test.com',
                 '_path': '/subitem2',
                 '_backlinks': {'http://www.test.com/item1': ''},
                 'title': 'subitem2 title',
                 'image': 'subitem2 image content',
                 '_type': 'Image'},
            )
    provideUtility(MakeAttachmentsSource,
        name=u'pretaweb.blueprints.tests.makeattachments')
    provideUtility(MakeAttachments,
        name=u'pretaweb.blueprints.makeattachments')


def test_suite():
    return unittest.TestSuite((
        doctest.DocFileSuite('webcrawler.txt', setUp=setUp, tearDown=tearDown),
        doctest.DocFileSuite('treeserializer.txt', setUp=setUp, tearDown=tearDown),
        doctest.DocFileSuite('typerecognitor.txt', setUp=setUp, tearDown=tearDown),
        doctest.DocFileSuite('templatefinder.txt', setUp=setUp, tearDown=tearDown),
        doctest.DocFileSuite('relinker.txt', setUp=setUp, tearDown=tearDown),
        doctest.DocFileSuite('pathmover.txt', setUp=setUp, tearDown=tearDown),
        doctest.DocFileSuite('simplexpath.txt', setUp=setUp, tearDown=tearDown),
        doctest.DocFileSuite('safeatschemaupdater.txt',
                setUp=SafeATSchemaUpdaterSetUp,
                tearDown=tearDown),
        doctest.DocFileSuite('makeattachments.txt',
                setUp=MakeAttachmentsSetUp,
                tearDown=tearDown),
    ))

