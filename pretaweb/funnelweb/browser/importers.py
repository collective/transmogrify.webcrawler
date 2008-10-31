# -*- coding: utf-8 -*-

from Acquisition import aq_inner
from zope.component import getUtility

from Products.CMFCore.interfaces import ISiteRoot
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from collective.transmogrifier.transmogrifier import Transmogrifier
from collective.transmogrifier.transmogrifier import configuration_registry
from os.path import dirname, abspath
import urllib
from collective.transmogrifier.tests import registerConfig
from collective.transmogrifier.transmogrifier import Transmogrifier


class Import(BrowserView):

    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)
        self.ids = configuration_registry.listConfigurationIds()
        self.ids = ['Automatic SiteSucker'] + list(self.ids)

    def test(self, id=None, url=None):
        # run transmogrifier
        if url:
            here = abspath(dirname(__file__))
            config = open(here+'/funnelweb.cfg').read()
            config = config % url
            id = u'pretaweb.funnelweb.transmogrifier'
            registerConfig(id, config)
            transmogrifier = Transmogrifier(self.context)
            transmogrifier(id)
            return "ok"
        if id:
            transmogrifier = Transmogrifier(self.context)
            transmogrifier(id)
            return 'ok'
        else:
            return self.__template__()


    __call__ = test
    __template__ = ViewPageTemplateFile('imported.pt')
    #def __call__(self, *argv, **kw):
    #    # TODO :: should send message that imort happened
    #    return self.request.RESPONSE.redirect(self.context.absolute_url())


