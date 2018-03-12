import gobject
import gtk
import threading
import traceback
try:
    import pynotify
except ImportError:
    pynotify = None

from gui_o_matic.gui.base import BaseGUI


class GtkBaseGUI(BaseGUI):

    _HAVE_INDICATOR = False

    def __init__(self, config):
        BaseGUI.__init__(self, config)
        self.splash = None
        if pynotify:
            pynotify.init(config.get('app_name', 'gui-o-matic'))
        gobject.threads_init()

    def _menu_setup(self):
        self.items = {}
        self.menu = gtk.Menu()
        self._create_menu_from_config()

    def _add_menu_item(self, item=None, label='Menu item',
                             sensitive=False,
                             separator=False,
                             op=None, args=None,
                             **ignored_kwarg):
        if separator:
            menu_item = gtk.SeparatorMenuItem()
        else:
            menu_item = gtk.MenuItem(label)
            menu_item.set_sensitive(sensitive)
            if op:
                def activate(o, a):
                    return lambda d: self._do(o, a)
                menu_item.connect("activate", activate(op, args or []))
        menu_item.show()
        self.menu.append(menu_item)
        if item:
            self.items[item] = menu_item

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
            elif action['type'] == 'checkbox':
                widget = gtk.CheckButton(label=action.get('label', '?'))
                if action.get('checked'):
                    widget.set_active(True)
                event = "toggled"
            else:
                raise NotImplementedError('We only have buttons atm.')

            if action.get('position', 'left') in ('first', 'left', 'top'):
                button_box.pack_start(widget, False, True)
            elif action['position'] in ('last', 'right', 'bottom'):
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

    def _main_window_indicator(self, menu_container, icon_container):
        if not self._HAVE_INDICATOR:
            menubar = gtk.MenuBar()
            im = gtk.MenuItem(self.config.get('app_name', 'GUI-o-Matic'))
            im.set_submenu(self.menu)
            menubar.append(im)
            menu_container.pack_start(menubar, False, True)

            icon = gtk.Image()
            icon_container.pack_start(icon, False, True)
            self.main_window['indicator_icon'] = icon

    def _main_window_default_style(self):
        wcfg = self.config['main_window']
        vbox = gtk.VBox(False, 5)
        vbox.set_border_width(5)

        # TODO: Allow user to configure alignment of message, padding?

        lbl = gtk.Label()
        lbl.set_markup(wcfg.get('message', ''))
        lbl.set_alignment(0.0, 0.5)

        if wcfg.get('image'):
            self._set_background_image(vbox, wcfg.get('image'))

        button_box = gtk.HBox(False, 5)

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

    def _main_window_setup(self, _now=False):
        def create(self):
            wcfg = self.config['main_window']

            window = gtk.Window(gtk.WINDOW_TOPLEVEL)
            self.main_window = {'window': window}

            if wcfg.get('style', 'default') == 'default':
                self._main_window_default_style()
            else:
                raise NotImplementedError('We only have one style atm.')

            if wcfg.get('close_quits'):
                window.connect('delete-event', lambda w, e: gtk.main_quit())
            else:
                window.connect('delete-event', lambda w, e: w.hide() or True)
            window.connect("destroy", lambda wid: gtk.main_quit())

            window.set_title(self.config.get('app_name', 'gui-o-matic'))
            window.set_decorated(True)
            if wcfg.get('center', False):
                window.set_position(gtk.WIN_POS_CENTER)
            window.set_size_request(
                wcfg.get('width', 360), wcfg.get('height',360))
            if wcfg.get('show'):
                window.show_all()

        if _now:
            create(self)
        else:
            gobject.idle_add(create, self)

    def quit(self):
        def q(self):
            gtk.main_quit()
        gobject.idle_add(q, self)

    def show_main_window(self):
        def show(self):
            if self.main_window:
                self.main_window['window'].show_all()
        gobject.idle_add(show, self)

    def hide_main_window(self):
        def hide(self):
            if self.main_window:
                self.main_window['window'].hide()
        gobject.idle_add(hide, self)

    def update_splash_screen(self, progress=None, message=None, _now=False):
        def update(self):
            if self.splash:
                if message is not None and 'message' in self.splash:
                    self.splash['message'].set_markup(
                        message.replace('<', '&lt;'))
                if progress is not None and 'progress' in self.splash:
                    self.splash['progress'].set_fraction(progress)
        if _now:
            update(self)
        else:
            gobject.idle_add(update, self)

    def show_splash_screen(self, height=None, width=None,
                           progress_bar=False, image=None, message=None,
                           message_x=0.5, message_y=0.5,
                           _now=False):
        wait_lock = threading.Lock()
        def show(self):
            self.hide_splash_screen(_now=True)

            window = gtk.Window(gtk.WINDOW_TOPLEVEL)
            vbox = gtk.VBox(False, 1)

            if message:
                lbl = gtk.Label()
                lbl.set_markup(message or '')
                lbl.set_alignment(message_x, message_y)
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

            self.splash = {
                'window': window,
                'message_x': message_x,
                'message_y': message_y,
                'vbox': vbox,
                'message': lbl,
                'progress': pbar}
            wait_lock.release()
        with wait_lock:
            if _now:
                show(self)
            else:
                gobject.idle_add(show, self)
            wait_lock.acquire()

    def hide_splash_screen(self, _now=False):
        wait_lock = threading.Lock()
        def hide(self):
            for k in self.splash or []:
                if hasattr(self.splash[k], 'destroy'):
                    self.splash[k].destroy()
            self.splash = None
            wait_lock.release()
        with wait_lock:
            if _now:
                hide(self)
            else:
                gobject.idle_add(hide, self)
            wait_lock.acquire()

    def notify_user(self, message='Hello', popup=False):
        def notify(self):
            if 'status' in self.items:
                self.items['status'].set_label(message)
            if popup and pynotify:
                notification = pynotify.Notification(
                    self.config.get('app_name', 'gui-o-matic'),
                    message, "dialog-warning")
                notification.set_urgency(pynotify.URGENCY_NORMAL)
                notification.show()
            elif popup:
                print('FIXME: Notify: %s' % message)
            elif self.splash:
                self.update_splash_screen(message=message, _now=True)
            elif self.main_window:
                self.main_window['label'].set_markup(
                    message.replace('<', '&lt;'))
            else:
                print('FIXME: Notify: %s' % message)
        gobject.idle_add(notify, self)

    def _indicator_setup(self):
        pass

    def _indicator_set_icon(self, icon, **kwargs):
        if 'indicator_icon' in self.main_window:
            themed_icon = self._theme_image(icon)
            img = gtk.gdk.pixbuf_new_from_file(themed_icon)
            img = img.scale_simple(32, 32, gtk.gdk.INTERP_BILINEAR)
            self.main_window['indicator_icon'].set_from_pixbuf(img)

    def _indicator_set_status(self, status, **kwargs):
        pass

    def set_status(self, status='startup', _now=False):
        if _now:
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

        def ready(s):
            s.ready = True
        gobject.idle_add(ready, self)

        try:
            gtk.main()
        except:
            traceback.print_exc()


GUI = GtkBaseGUI
