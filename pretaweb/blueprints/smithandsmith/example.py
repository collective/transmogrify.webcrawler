# -*- coding: utf-8 -*-

from Acquisition import aq_inner
from zope.component import getUtility

from Products.CMFCore.interfaces import ISiteRoot
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from collective.transmogrifier.transmogrifier import Transmogrifier


class ExampleImport(BrowserView):

    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)

    def test(self):
        # run transmogrifier
        transmogrifier = Transmogrifier(self.context)
        transmogrifier(u'smithandsmithimport')
        return 'ok'


    __call__ = ViewPageTemplateFile('example.pt')
    #def __call__(self, *argv, **kw):
    #    # TODO :: should send message that imort happened
    #    return self.request.RESPONSE.redirect(self.context.absolute_url())


