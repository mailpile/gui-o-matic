# This is a general-purpose GUI which can be configured and controlled
# using a very simple line-based (JSON) protocol.
#
import appindicator
import gobject
import gtk
import traceback
try:
    import pynotify
except ImportError:
    pynotify = None

from base import BaseGUI


ICON_THEME = 'light'


class UnityWebView():
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


class UnityGUI(BaseGUI):
    def __init__(self, config):
        BaseGUI.__init__(self, config)
        if pynotify:
            pynotify.init(config.get('app_name', 'gui-o-matic'))
        gobject.threads_init()
        self.splash = None

    def _menu_setup(self):
        self.items = {}
        self.menu = gtk.Menu()
        self._create_menu_from_config()

    def _add_menu_item(self, item='item', label='Menu item',
                             sensitive=False,
                             op=None, args=None,
                             **ignored_kwarg):
        menu_item = gtk.MenuItem(label)
        menu_item.set_sensitive(sensitive)
        if op:
            def activate(o, a):
                return lambda d: self._do(o, a)
            menu_item.connect("activate", activate(op, args or []))
        menu_item.show()
        self.items[item] = menu_item
        self.menu.append(menu_item)

    def _ind_setup(self):
        self.ind = appindicator.Indicator(
            self.config.get('app_name', 'gui-o-matic').lower() + "-indicator",
            # FIXME: Make these two configurable...
            "indicator-messages", appindicator.CATEGORY_COMMUNICATIONS)
        self.set_status('startup', now=True)
        self.ind.set_menu(self.menu)

    def update_splash_screen(self, progress=None, message=None):
        if self.splash:
            if message is not None and 'message' in self.splash:
                self.splash['message'].set_markup(message)
            if progress is not None and 'progress' in self.splash:
                self.splash['progress'].set_fraction(progress)

    def show_splash_screen(self, height=None, width=None,
                           progress_bar=False, image=None, message=None,
                           now=False):
        def show(self):
            window = gtk.Window(gtk.WINDOW_TOPLEVEL)
            vbox = gtk.VBox(False, 1)

            if message:
                lbl = gtk.Label()
                lbl.set_markup(message or '')
                lbl.set_alignment(0.5, 0.5)
                vbox.pack_start(lbl, True, True)
            else:
                lbl = None

            if image:
                themed_image = self._theme_image(image)
                img = gtk.gdk.pixbuf_new_from_file(themed_image)
                def draw_background(widget, ev):
                    alloc = widget.get_allocation()
                    pb = img.scale_simple(alloc.width, alloc.height,
                                          gtk.gdk.INTERP_BILINEAR)
                    widget.window.draw_pixbuf(
                        widget.style.bg_gc[gtk.STATE_NORMAL],
                        pb, 0, 0, alloc.x, alloc.y)
                    if (hasattr(widget, 'get_child') and
                            widget.get_child() is not None):
                        widget.propagate_expose(widget.get_child(), ev)
                    return False
                vbox.connect('expose_event', draw_background)

            if progress_bar:
                pbar = gtk.ProgressBar()
                pbar.set_orientation(gtk.PROGRESS_LEFT_TO_RIGHT)
                vbox.pack_end(pbar, False, True)
            else:
                pbar = None

            window.set_title(self.config.get('app_name', 'gui-o-matic'))
            window.set_decorated(False)
            window.set_position(gtk.WIN_POS_CENTER)
            window.set_size_request(width or 240, height or 320)
            window.add(vbox)
            window.show_all()

            self.hide_splash_screen(now=True)
            self.splash = {
                'window': window,
                'vbox': vbox,
                'message': lbl,
                'progress': pbar
            }
        if now:
            show(self)
        else:
            gobject.idle_add(show, self)

    def hide_splash_screen(self, now=False):
        def hide(self):
            for k in self.splash or []:
                if self.splash[k] is not None:
                    self.splash[k].destroy()
            self.splash = None
        if now:
            hide(self)
        else:
            gobject.idle_add(hide, self)

    def _get_webview(self):
        if not self._webview:
            try:
                self._webview = UnityWebView(self)
            except ImportError:
                pass
        return self._webview

    def notify_user(self, message='Hello'):
        if pynotify:
            notification = pynotify.Notification(
                self.config.get('app_name', 'gui-o-matic'),
                message, "dialog-warning")
            notification.set_urgency(pynotify.URGENCY_NORMAL)
            notification.show()
        else:
            print('FIXME: Notify: %s' % message)

    _STATUS_MODES = {
        'startup': appindicator.STATUS_ACTIVE,
        'normal': appindicator.STATUS_ACTIVE,
        'working': appindicator.STATUS_ACTIVE,
        'attention': appindicator.STATUS_ATTENTION,
        'shutdown': appindicator.STATUS_ATTENTION,
    }
    def set_status(self, status='startup', now=False):
        if now:
            do = lambda o, a: o(a)
        else:
            do = gobject.idle_add
        if 'indicator_icons' in self.config:
            icon = self.config['indicator_icons'].get(status)
            if not icon:
                icon = self.config['indicator_icons'].get('normal')
            if icon:
                do(self.ind.set_icon, self._theme_image(icon))
        do(self.ind.set_status,
           self._STATUS_MODES.get(status, appindicator.STATUS_ATTENTION))

    def set_menu_label(self, item=None, label=None):
        if item and item in self.items:
            gobject.idle_add(self.items[item].set_label, label)

    def set_menu_sensitive(self, item=None, sensitive=True):
        if item and item in self.items:
            gobject.idle_add(self.items[item].set_sensitive, sensitive)

    def run(self):
        self._menu_setup()
        self._ind_setup()
        self.ready = True
        try:
            gtk.main()
        except:
            traceback.print_exc()


GUI = UnityGUI
