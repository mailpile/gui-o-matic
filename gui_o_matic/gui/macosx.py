# This is a general-purpose GUI which can be configured and controlled
# using a very simple line-based (JSON) protocol.
#
import objc
import traceback

from Foundation import *
from AppKit import *
from PyObjCTools import AppHelper

from base import BaseGUI


class MacOSXThing(NSObject):
    indicator = None

    def applicationDidFinishLaunching_(self, notification):
        self.indicator._menu_setup()
        self.indicator._ind_setup()
        self.indicator.ready = True

    def activate_(self, notification):
        for i, v in self.indicator.items.iteritems():
            if notification == v:
                if i in self.indicator.callbacks:
                    self.indicator.callbacks[i]()
                return
        print('activated an unknown item: %s' % notification)


class MacOSXGUI(BaseGUI):

    ICON_THEME = 'osx'  # OS X has its own theme because it is too
                        # dumb to auto-resize menu bar icons.

    def _menu_setup(self):
        # Build a very simple menu
        self.menu = NSMenu.alloc().init()
        self.menu.setAutoenablesItems_(objc.NO)
        self.items = {}
        self.callbacks = {}
        self._create_menu_from_config()

    def _add_menu_item(self, item='item', label='Menu item',
                             sensitive=False,
                             op=None, args=None,
                             **ignored_kwarg):
        # For now, bind everything to the notify method
        menuitem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            label, 'activate:', '')
        menuitem.setEnabled_(sensitive)
        self.menu.addItem_(menuitem)
        self.items[item] = menuitem
        if op:
            def activate(o, a):
                return lambda: self._do(o, a)
            self.callbacks[item] = activate(op, args or [])

    def _ind_setup(self):
        # Create the statusbar item
        self.ind = NSStatusBar.systemStatusBar().statusItemWithLength_(
            NSVariableStatusItemLength)

        # Load all images, set initial
        self.images = {}
        icons = self.config.get('indicator', {}).get('icons', {})
        for s, p in icons.iteritems():
            p = self._theme_image(p)
            self.images[s] = NSImage.alloc().initByReferencingFile_(p)
        if self.images:
            self.ind.setImage_(self.images['normal'])

        self.ind.setHighlightMode_(1)
        #self.ind.setToolTip_('Sync Trigger')
        self.ind.setMenu_(self.menu)
        self.set_status()

    def set_status(self, status='startup'):
        self.ind.setImage_(self.images.get(status, self.images['normal']))

    def set_item_label(self, item=None, label=None):
        if item and item in self.items:
            self.items[item].setTitle_(label)

    def set_item_sensitive(self, item=None, sensitive=True):
        if item and item in self.items:
            self.items[item].setEnabled_(sensitive)

    def notify_user(self, message=None):
        pass  # FIXME

    def run(self):
        app = NSApplication.sharedApplication()
        osxthing = MacOSXThing.alloc().init()
        osxthing.indicator = self
        app.setDelegate_(osxthing)
        try:
            AppHelper.runEventLoop()
        except:
            traceback.print_exc()


GUI = MacOSXGUI
