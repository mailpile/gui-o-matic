# This is a general-purpose GUI which can be configured and controlled
# using a very simple line-based (JSON) protocol.
#
import appindicator
import gobject
import gtk

from gui_o_matic.gui.gtkbase import GtkBaseGUI


class UnityGUI(GtkBaseGUI):
    _HAVE_INDICATOR = True
    _STATUS_MODES = {
        'startup': appindicator.STATUS_ACTIVE,
        'normal': appindicator.STATUS_ACTIVE,
        'working': appindicator.STATUS_ACTIVE,
        'attention': appindicator.STATUS_ATTENTION,
        'shutdown': appindicator.STATUS_ATTENTION,
    }

    def _indicator_setup(self):
        self.ind = appindicator.Indicator(
            self.config.get('app_name', 'gui-o-matic').lower() + "-indicator",
            # FIXME: Make these two configurable...
            "indicator-messages", appindicator.CATEGORY_COMMUNICATIONS)
        self.set_status('startup', _now=True)
        self.ind.set_menu(self.menu)

    def _indicator_set_icon(self, icon, do=gobject.idle_add):
        do(self.ind.set_icon, self._theme_image(icon))

    def _indicator_set_status(self, status, do=gobject.idle_add):
        do(self.ind.set_status,
           self._STATUS_MODES.get(status, appindicator.STATUS_ATTENTION))


GUI = UnityGUI
