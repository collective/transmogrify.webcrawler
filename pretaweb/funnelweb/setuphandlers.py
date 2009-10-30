"""Generic Setup stuff"""

import zope.event
import zope.interface
import zope.component.interfaces
from zope.component import adapter
#import lovely
from AccessControl.Role import RoleManager
from OFS.SimpleItem import Item

#class FunnelwebService(Item, lovely.remotetask.TaskService):
#    pass

def import_various(context):
    if context.readDataFile('pretaweb.funnelweb-various.txt') is None:
        return

    portal = context.getSite()
    zope.event.notify(SiteInstalledEvent(portal))

    sm = portal.getSiteManager()
#    if not sm.queryUtility(lovely.remotetask.interfaces.ITaskService, name="FunnelwebService"):
 #       service = FunnelwebService()
 #       service.id = "funnelwebservice"
 #       sm.registerUtility(service,
 #                          lovely.remotetask.interfaces.ITaskService,
 #                          name="FunnelwebService")
 #       portal['funnelwebservice'] = service



class ISiteInstalledEvent(zope.component.interfaces.IObjectEvent):
    """Event, raised after Funnelweb installation"""


class SiteInstalledEvent(zope.component.interfaces.ObjectEvent):
    zope.interface.implements(ISiteInstalledEvent)


@adapter(None, ISiteInstalledEvent)
def install_service(portal, event):
    pass

