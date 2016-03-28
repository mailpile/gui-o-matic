import gobject
import gtk
import traceback
try:
    import pynotify
except ImportError:
    pynotify = None

from base import BaseGUI


class GtkBaseGUI(BaseGUI):

    _HAVE_INDICATOR = False

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

    def _set_background_image(self, container, image):
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
        container.connect('expose_event', draw_background)

    def _main_window_add_actions(self, button_box):
        for action in self.config['main_window'].get('actions', []):
            if action.get('type', 'button') == 'button':
                widget = gtk.Button(label=action.get('label', 'OK'))
                event = "clicked"
            else:
                raise NotImplementedError('We only have buttons atm.')

            if action.get('position', 'left') in ('left', 'top'):
                button_box.pack_start(widget, False, True)
            elif action['position'] in ('right', 'bottom'):
                button_box.pack_end(widget, False, True)
            else:
                raise NotImplementedError('Invalid position: %s'
                                          % action['position'])

            if action.get('op'):
                def activate(o, a):
                    return lambda d: self._do(o, a)
                widget.connect(event,
                    activate(action['op'], action.get('args', [])))

            widget.set_sensitive(action.get('sensitive', True))
            self.items[action['item']] = widget

    def _main_window_menubar(self, menu_container, icon_container):
        if not self._HAVE_INDICATOR:
            menubar = gtk.MenuBar()
            im = gtk.MenuItem(self.config.get('app_name', 'GUI-o-Matic'))
            im.set_submenu(self.menu)
            menubar.append(im)
            menu_container.pack_start(menubar, False, True)

            # FIXME: Create indicator icon, put in the container and
            #        wire things up so _indicator_set_icon() can do
            #        its thing.

    def _main_window_default_style(self):
        wcfg = self.config['main_window']
        vbox = gtk.VBox(False, 1)

        # TODO: Allow user to configure alignment of message, padding?

        lbl = gtk.Label()
        lbl.set_markup(wcfg.get('message', ''))
        lbl.set_alignment(0.5, 0.5)

        if wcfg.get('image'):
            self._set_background_image(vbox, wcfg.get('image'))

        button_box = gtk.HBox(False, 1)
        self._main_window_indicator(vbox, button_box)
        self._main_window_add_actions(button_box)

        vbox.pack_start(lbl, True, True)
        vbox.pack_end(button_box, False, True)
        self.main_window['window'].add(vbox)
        self.main_window.update({
            'vbox': vbox,
            'label': lbl,
            'buttons': button_box})

    # TODO: Add other window styles?

    def _main_window_setup(self, now=False):
        def create(self):
            wcfg = self.config['main_window']

            window = gtk.Window(gtk.WINDOW_TOPLEVEL)
            self.main_window = {'window': window}

            if wcfg.get('style', 'default') == 'default':
                self._main_window_default_style()
            else:
                raise NotImplementedError('We only have one style atm.')

            if wcfg.get('close_quits'):
                window.connect("delete_event", lambda a1,a2: gtk.main_quit())
            else:
                window.connect('delete-event', lambda w, e: w.hide() or True)
            window.connect("destroy", lambda wid: gtk.main_quit())

            window.set_title(self.config.get('app_name', 'gui-o-matic'))
            window.set_decorated(True)
            window.set_size_request(
                wcfg.get('width', 360), wcfg.get('height',360))
            if wcfg.get('show'):
                window.show_all()

        if now:
            create(self)
        else:
            gobject.idle_add(create, self)

    def quit(self):
        gtk.main_quit()

    def show_main_window(self):
        if self.main_window:
            self.main_window['window'].show_all()

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
                self._set_background_image(vbox, image)

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
                # FIXME: This is broken
                self._webview = UnityWebView(self)
            except (ImportError, NameError):
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

    def _indicator_setup(self):
        pass

    def _indicator_set_icon(self, icon, **kwargs):
        # FIXME: Update an icon in the main window instead.
        pass

    def _indicator_set_status(self, status, **kwargs):
        pass

    def set_status(self, status='startup', now=False):
        if now:
            do = lambda o, a: o(a)
        else:
            do = gobject.idle_add
        icons = self.config.get('indicator', {}).get('icons')
        if icons:
            icon = icons.get(status)
            if not icon:
                icon = icons.get('normal')
            if icon:
                self._indicator_set_icon(icon, do=do)
        self._indicator_set_status(status, do=do)

    def set_item_label(self, item=None, label=None):
        if item and item in self.items:
            gobject.idle_add(self.items[item].set_label, label)

    def set_item_sensitive(self, item=None, sensitive=True):
        if item and item in self.items:
            gobject.idle_add(self.items[item].set_sensitive, sensitive)

    def run(self):
        self._menu_setup()
        if self.config.get('indicator') and self._HAVE_INDICATOR:
            self._indicator_setup()
        if self.config.get('main_window'):
            self._main_window_setup()

        self.ready = True
        try:
            gtk.main()
        except:
            traceback.print_exc()


GUI = GtkBaseGUI
