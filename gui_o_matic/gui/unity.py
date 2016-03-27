# This is a general-purpose GUI which can be configured and controlled
# using a very simple line-based (JSON) protocol.
#
import appindicator
import gobject
import gtk

from gtkbase import GtkBaseGUI


class UNUSED_UnityWebView():
    def __init__(self, mpi):
        import webkit
        self.webview = webkit.WebView()

        self.scroller = gtk.ScrolledWindow()
        self.scroller.add(self.webview)

        self.vbox = gtk.VBox(False, 1)
        self.vbox.pack_start(self.scroller, True, True)

        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_size_request(1100, 600)
        self.window.connect('delete-event', lambda w, e: w.hide() or True)
        self.window.add(self.vbox)

        self.browser_settings = self.webview.get_settings()
        self.browser_settings.set_property("enable-java-applet", False)
        self.browser_settings.set_property("enable-plugins", False)
        self.browser_settings.set_property("enable-scripts", True)
        self.browser_settings.set_property("enable-private-browsing", True)
        self.browser_settings.set_property("enable-spell-checking", True)
        self.browser_settings.set_property("enable-developer-extras", True)
        self.webview.set_settings(self.browser_settings)

    def show_url(self, url):
        self.webview.open('about:blank')  # Clear page while loading
        self.webview.open(url)
        self.window.show_all()


class UnityGUI(GtkBaseGUI):
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
        self.set_status('startup', now=True)
        self.ind.set_menu(self.menu)

    def _indicator_set_icon(self, icon, do=gobject.idle_add):
        do(self.ind.set_icon, self._theme_image(icon))

    def _indicator_set_status(self, status, do=gobject.idle_add):
        do(self.ind.set_status,
           self._STATUS_MODES.get(status, appindicator.STATUS_ATTENTION))


GUI = UnityGUI
