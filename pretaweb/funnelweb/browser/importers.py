# -*- coding: utf-8 -*-

from Acquisition import aq_inner
from zope.component import getUtility, adapter, provideUtility

from Products.CMFCore.interfaces import ISiteRoot
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from collective.transmogrifier.transmogrifier import Transmogrifier
from collective.transmogrifier.transmogrifier import configuration_registry
from os.path import dirname, abspath
import urllib
from collective.transmogrifier.tests import registerConfig
from collective.transmogrifier.transmogrifier import Transmogrifier

from z3c.form.form import Form
from z3c.form.field import Fields
from z3c.form.button import buttonAndHandler
from z3c.form.interfaces import HIDDEN_MODE, INPUT_MODE, DISPLAY_MODE
from plone.app.z3cform.layout import wrap_form
from plone.app.z3cform.layout import FormWrapper
from z3c.form.browser import checkbox
from z3c.form import field, group
from Products.statusmessages.interfaces import IStatusMessage
from kss.core import KSSView, kssaction


from pretaweb.funnelweb import FunnelwebMessageFactory as _
#_ = lambda x:x


from zope import schema
from zope.interface import Interface
from zope.annotation.interfaces import IAnnotatable
from plone.theme.interfaces import IDefaultPloneLayer
from pretaweb.funnelweb.interfaces import ISectionFeedback
import lovely
from pretaweb.funnelweb.setuphandlers import ISiteInstalledEvent


class IFunnelwebForm(Interface):
    """  """
    base_url = schema.URI(
        title       = u'Import URL',
        description = u'The crawler will only crawler the site with URLs that begin with this URL',
        required    = True,
        )

    ignore_urls = schema.Text(
        title       = u'URLs to ignore',
        required    = False,
        description = u'The crawler will ignore URLs which match these patterns',
        default     = u"""\
cgi-bin
javascript:"""
        )

    ignore_minetypes = schema.Text(
        title       = u'Mimetypes to ignore',
        required    = False,
        description = u"The crawler will also ignore certain mimetype if you don't wish to import these",
#        value_type  = schema.TextLine(),
        default     = u"""\
application/x-javascript
text/css
application/x-java-byte-code\
"""
        )

    title_xpath = schema.TextLine(
        title       = u'Title XPath',
        required    = False,
        )

    description_xpath = schema.TextLine(
        title       = u'Description XPath',
        required    = False,
        )

    body_xpath = schema.TextLine(
        title       = u'Body XPath',
        required    = False,
        )

    index_analyser = schema.Bool(
        title       = u'Enable Index Analyser',
        required    = False,
        default     = True,
        )

    convert_mimetypes = schema.Text(
        title       = u'Mimetypes to convert',
        required    = False,
 #       value_type  = schema.TextLine(),
 #       default     = ""
        )

    attachment_analyser = schema.Bool(
        title       = u'Enable Attachment Analyser',
        required    = False,
        default     = True,
        )


    title_analyser = schema.Bool(
        title       = u'Enable Title Analyser',
        required    = False,
        default     = True,
        )

    constructor = schema.Bool(
        title       = u'Enable Construct Content',
        required    = False,
        default     = True,
        )

    overwrite = schema.Bool(
        title       = u'Overwrite existing content',
        required    = False,
        default     = True,
        )

    moved_content = schema.Bool(
        title       = u'Overwrite moved content',
        required    = False,
        default     = True,
        )

    publish_content = schema.TextLine(
        title       = u'State for imported content',
        required    = False,
        default     = u'Publish',
        )

    results = schema.TextLine(
        title       = u'Results',
        required    = False,
        default     = u'',
        )
#  ['No Change','Published','Review','Private']




class WebcrawlerGroup(group.Group):
    label = u'Webcrawler'
    fields = field.Fields(IFunnelwebForm).select(
        'base_url', 'ignore_urls', 'ignore_minetypes')
    description = """Collects the web pages from the external site."""

class TemplateGroup(group.Group):
    label = u'Template Analyser'
    description = """\
Content Extractor performs an analysis on all the pages collected. It will determine what is unique
content on each page and extract it. If the analysis fails you can override it with an XPath expressions.
"""
    fields = field.Fields(IFunnelwebForm).select(
        'title_xpath', 'description_xpath', 'body_xpath')

class IndexGroup(group.Group):
    label = u'Index Analyser'
    description = u"Index Analyser will try to determine which content should the default content for a folder view"
    fields = field.Fields(IFunnelwebForm).select(
        'index_analyser',)
    fields['index_analyser'].widgetFactory[INPUT_MODE] = checkbox.SingleCheckBoxFieldWidget

class DocumentGroup(group.Group):
    label = u'Document Conversion'
    description = u"""\
Converts non-HTML content into HTML so they can be edited in Plone
"""
    fields = field.Fields(IFunnelwebForm).select(
        'convert_mimetypes', )

class AttachmentGroup(group.Group):
    label = u'Attachment Analyser'
    description = u"""\
Finds images and pages which are only linked from one location and move them
into the same location.
"""
    fields = field.Fields(IFunnelwebForm).select(
        'attachment_analyser',)
    fields['attachment_analyser'].widgetFactory[INPUT_MODE] = checkbox.SingleCheckBoxFieldWidget

class TitlesGroup(group.Group):
    label = u'Title Analyser'
    description = u"Looks for better titles for content by using anchor text"
    fields = field.Fields(IFunnelwebForm).select(
        'title_analyser',)
    fields['title_analyser'].widgetFactory[INPUT_MODE] = checkbox.SingleCheckBoxFieldWidget

class ConstructGroup(group.Group):
    label = u'Content Importer'
    description = u"Construct new content or overwrite existing content in the current folder"
    fields = field.Fields(IFunnelwebForm).select(
        'constructor', 'overwrite', 'moved_content', 'publish_content')
    fields['constructor'].widgetFactory[INPUT_MODE] = checkbox.SingleCheckBoxFieldWidget
    fields['overwrite'].widgetFactory[INPUT_MODE] = checkbox.SingleCheckBoxFieldWidget
    fields['moved_content'].widgetFactory[INPUT_MODE] = checkbox.SingleCheckBoxFieldWidget




class FunnelwebForm(group.GroupForm, Form):

    label = _(u'Import Website')
#    fields = Fields(IFunnelwebForm)
    groups = (WebcrawlerGroup,
              TemplateGroup,
              IndexGroup,
              DocumentGroup,
              AttachmentGroup,
              TitlesGroup,
              ConstructGroup)
    ignoreContext = True
    fields = field.Fields(IFunnelwebForm).select('results')

    def __init__(self, context, request):
        super(FunnelwebForm, self).__init__(context, request)
        sm = context.getSiteManager()
        self.service = sm.getUtility(lovely.remotetask.interfaces.ITaskService, name="FunnelwebService")
        self.jobid = self.context.REQUEST.SESSION.get('jobid')


    def updateWidgets(self):
        Form.updateWidgets(self)
        if self.jobid is not None and self.service.getResult(self.jobid) is None:
            self.widgets['results'].mode = DISPLAY_MODE
        else:
            self.widgets['results'].mode = HIDDEN_MODE

    @buttonAndHandler(_(u'Start Import'))
    def submit(self, action):
        data, errors = self.extractData()
        if errors: return False

        transmogrifier = Transmogrifier(self.context)
        feedback = ISectionFeedback(transmogrifier)
        overrides = {}
        if data['base_url'] or data['ignore_urls']:
            overrides['webcrawler'] = dict(
#                    blueprint = "pretaweb.funnelweb.webcrawler",
                    site_url  = data['base_url'],
                    ignore = data.get('ignore_urls',''),
                )
        if data['title_xpath'] or data['body_xpath'] or data['description_xpath']:
           overrides['templatefinder']=dict(
#                    #blueprint = pretaweb.funnelweb.templatefinder,
                    auto=True,
                    title=data.get('title_xpath',''),
                    text=data.get('body_xpath',''),
            )
        if data['convert_mimetypes']:
            m = str([m.strip() for m in data['convert_mimetypes'].split('\n')])
            overrides['todrop'] = dict(
                condition = "python:item.get('_mimetype') not in %s and item.get('_path','').split('.')[-1] not in ['class']"%m
                )
        if not data['index_analyser']:
            overrides['isindex'] = None
        if data['convert_mimetypes']:
            m = str([m.strip() for m in data['convert_mimetypes'].split('\n')])
            overrides['transform-doc'] = dict(
                condition = 'python:item.get("_mimetype") in %s'% m
                )
        if not data['attachment_analyser']:
            overrides['makeattachments'] = None

        if not data['title_analyser']:
            overrides['title_from_link'] = None
        if not data['constructor']:
            overrides['constructor'] = None
        if not data['overwrite']:
            #TODO
            pass
        if not data['moved_content']:
            #TODO
            pass
        if data['publish_content']:
            m = str([m.strip() for m in data['publish_content'].split('\n')])
            overrides['publish'] = dict(
                value = "python:%s"%m
                )

        #registerConfig(id, config)
        self.context.REQUEST.SESSION.set('funnelwebfeedback', feedback)

        def runfunnelweb():
            id = u'pretaweb.funnelweb.transmogrifier'
#            import pdb;pdb.set_trace()
            transmogrifier(id, **overrides)
        runfunnelweb()
        #fwTask = lovely.remotetask.task.SimpleTask(runfunnelweb)
        #provideUtility(fwTask, name='runfunnelweb')
        #self.jobid = self.service.add(u'runfunnelweb')
        #if not self.service.isProcessing():
        #    self.service.startProcessing() #in case it isn't already
        self.context.REQUEST.SESSION.set('jobid', self.jobid)


        wchit,wcignore = feedback.getTotals('webcrawler')
        updaterhit,updaterignore = feedback.getTotals('schemaupdater')
        msg = "Crawled %s pages and imported %s" % (wchit, updaterhit)
        IStatusMessage(self.request).addStatusMessage(msg, type='info')

        return True

##
## Progress archtecture
##
# We submit the request which then gets put into a queue and return a form with results pane on it.
# kss timeout will poll for result and fill in results.
# results will be stored in session or similar.
#



class ImportProgress(KSSView):

    @kssaction
    def funnelwebProgress(self):
        sm = self.context.getSiteManager()
        service = sm.getUtility(lovely.remotetask.interfaces.ITaskService, name="FunnelwebService")

        ksscore = self.getCommandSet('core')
        selector = ksscore.getHtmlIdSelector('form-widgets-results')
        session = self.context.REQUEST.SESSION
        jobid = session.get('jobid')
        if jobid:
            status = service.getStatus(jobid)
        else:
            status = None
        feedback = session.get('funnelwebfeedback')
        if feedback:
            wchit,wcignore = feedback.getTotals('webcrawler')
            updaterhit,updaterignore = feedback.getTotals('schemaupdater')
            msg = "Crawled %s pages and imported %s: %s" % (wchit, updaterhit, str(status))
            ksscore.replaceInnerHTML(selector, msg)
        else:
            ksscore.replaceInnerHTML(selector, status)


        return self.render()



FunnelwebView = wrap_form(FunnelwebForm)

class FunnelwebView(FormWrapper):
    form = FunnelwebForm
    label = u"Import website into current folder"


#class FunnelwebService(remotetask.TaskService):
#    implements(remotetask.interfacesITaskService)
#    pass

#from zope.component import provideAdapter
#from zope.publisher.interfaces.browser import IBrowserRequest
#from zope.interface import Interface

#provideAdapter(adapts=(Interface, IBrowserRequest),
#                provides=Interface,
#                factory=FunnelwebView,
#                name=u"test-form")
