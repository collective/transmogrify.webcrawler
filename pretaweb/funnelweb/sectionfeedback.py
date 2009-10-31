
from interfaces import ISectionFeedback
from zope.annotation.interfaces import IAnnotations
from zope.interface import classProvides
from zope.interface import implements




MYKEY = 'transmogrifier.sectionfeedback'

class SectionFeedback:
    """  Adapter for storing general feedback about transmogrifier progress """
    implements(ISectionFeedback)

    def __init__(self, transmogrifier):
        self.storage = IAnnotations(transmogrifier).setdefault(MYKEY, {})
        self.storage.setdefault('sections', {})

    def success(self, section, msg):
        ""
        sdata = self.storage.setdefault(section,{})
        total = sdata.setdefault('success_total',0)
        sdata['success_total'] += 1
        sdata.setdefault('msgs',[]).append((True,msg))

    def ignored(self, section, msg):
        ""
        sdata = self.storage.setdefault(section,{})
        total = sdata.setdefault('ignore_total',0)
        sdata['ignore_total'] += 1
        sdata.setdefault('msgs',[]).append((False,msg))

    def getTotals(self, section):
        sdata = self.storage.setdefault(section,{})
        return (sdata.get('success_total', 0), sdata.get('ignore_total', 0))


