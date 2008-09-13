# -*- coding: utf-8 -*-

from Acquisition import aq_inner
from zope.component import getUtility

from Products.CMFCore.interfaces import ISiteRoot
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from collective.transmogrifier.transmogrifier import Transmogrifier
from collective.transmogrifier.transmogrifier import configuration_registry


class Import(BrowserView):

    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)
        self.ids = configuration_registry.listConfigurationIds

    def test(self, id=None):
        # run transmogrifier
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


