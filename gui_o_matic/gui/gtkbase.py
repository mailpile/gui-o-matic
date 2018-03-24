import pango
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
        self.font_styles = {}
        self.substatus = {}
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

    def _set_substatus_icon(self, status, icon_path, size=32):
        if 'icon' in status:
            themed_icon = self._theme_image(icon_path)
            img = gtk.gdk.pixbuf_new_from_file(themed_icon)
            img = img.scale_simple(size, size, gtk.gdk.INTERP_BILINEAR)
            status['icon'].set_from_pixbuf(img)
            status['icon_size'] = size

    def _main_window_default_style(self):
        wcfg = self.config['main_window']
        vbox = gtk.VBox(False, 0)
        vbox.set_border_width(7)

        # Enforce that the window always has at least one status section,
        # even if the configuration doesn't specify one.
        stat_defs = wcfg.get("substatus") or [{"item": "status", "label": ""}]

        # Scale the status icons relative to a) how tall the window is,
        # and b) how many status lines we are showing.
        icon_size = int(0.66 * wcfg.get('height', 360) / len(stat_defs))

        substatuses = []
        for st in stat_defs:
            ss = {
                'item': st['item'],
                'hbox': gtk.HBox(False, 5),
                'vbox': gtk.VBox(False, 5),
                'label': gtk.Label(),
                'hint': gtk.Label()}

            for which in ('label', 'hint'):
                ss[which].set_markup(st.get(which, ''))
                if which in self.font_styles:
                    ss[which].modify_font(self.font_styles[which])

            if 'icon' in st:
                ss['icon'] = gtk.Image()
                ss['hbox'].pack_start(ss['icon'], False, True)
                self._set_substatus_icon(ss, st['icon'], icon_size)
                text_x = 0.0
            else:
                # If there is no icon, center our labels and hints.
                text_x = 0.5

            ss['label'].set_alignment(text_x, 1.0)
            ss['hint'].set_alignment(text_x, 0.0)
            ss['vbox'].pack_start(ss['label'], True, True)
            ss['vbox'].pack_end(ss['hint'], True, True)
            ss['vbox'].set_spacing(1)
            ss['hbox'].pack_start(ss['vbox'], True, True)
            ss['hbox'].set_spacing(7)
            substatuses.append(ss)
        self.substatus = dict((ss['item'], ss) for ss in substatuses)

        status = None
        if 'status' not in self.substatus:
            status = gtk.Label()
            status.set_markup(wcfg.get('label', ''))
            status.set_alignment(0, 0.5)
            if 'status' in self.font_styles:
                status.modify_font(self.font_styles['status'])

        if wcfg.get('image'):
            self._set_background_image(vbox, wcfg.get('image'))

        button_box = gtk.HBox(False, 5)

        self._main_window_indicator(vbox, button_box)
        self._main_window_add_actions(button_box)
        if status:
            button_box.pack_start(status, True, True)
        for ss in substatuses:
            vbox.pack_start(ss['hbox'], True, True)
        vbox.pack_end(button_box, False, True)

        self.main_window['window'].add(vbox)
        self.main_window.update({
            'vbox': vbox,
            'status': (status if status else self.substatus['status']['hint']),
            'substatuses': substatuses,
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
                if 'splash' in self.font_styles:
                    lbl.modify_font(self.font_styles['splash'])
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
            # We always update the indicator status with the latest
            # notification.
            if 'status' in self.items:
                self.items['status'].set_label(message)

            # Popups!
            if popup:
                popup_icon = 'dialog-warning'
                if 'app_icon' in self.config:
                    popup_icon = self._theme_image(self.config['app_icon'])
                popup_appname = self.config.get('app_name', 'gui-o-matic')
                if pynotify is not None:
                    notification = pynotify.Notification(
                        popup_appname, message, popup_icon)
                    notification.set_urgency(pynotify.URGENCY_NORMAL)
                    notification.show()
                    return
                elif not self.config.get('disable-popup-fallback'):
                    try:
                        if self._spawn([
                                    'notify-send',
                                    '-i', popup_icon, popup_appname,
                                    message],
                                report_errors=False):
                            return
                    except:
                        print('FIXME: Should popup: %s' % message)

            # Note: popups also fall through to here if we can't pop up
            if self.splash:
                self.update_splash_screen(message=message, _now=True)
            elif self.main_window:
                msg = message.replace('<', '&lt;')
                self.main_window['status'].set_markup(msg)
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
        images = self.config.get('images')
        if images:
            icon = images.get(status)
            if not icon:
                icon = images.get('normal')
            if icon:
                self._indicator_set_icon(icon, do=do)
        self._indicator_set_status(status, do=do)

    def set_substatus(self,
            substatus=None, label=None, hint=None, icon=None, color=None):
        status = self.substatus.get(substatus)
        if not status:
            return
        if icon:
            self._set_substatus_icon(status, icon, status.get('icon_size', 32))
        if label:
            status['label'].set_markup(label)
        if hint:
            status['hint'].set_markup(hint)
        if color:
            color = gtk.gdk.color_parse(color)
            for which in ('label', 'hint'):
                status[which].modify_fg(gtk.STATE_NORMAL, color)
                status[which].modify_text(gtk.STATE_NORMAL, color)

    def set_item_label(self, item=None, label=None):
        if item and item in self.items:
            gobject.idle_add(self.items[item].set_label, label)

    def set_item_sensitive(self, item=None, sensitive=True):
        if item and item in self.items:
            gobject.idle_add(self.items[item].set_sensitive, sensitive)

    def _font_setup(self):
        for name, style in self.config.get('font-styles', {}).iteritems():
            pfd = pango.FontDescription()
            pfd.set_family(style.get('family', 'normal'))
            pfd.set_size(style.get('points', 12) * pango.SCALE)
            if style.get('italic'): pfd.set_style(pango.STYLE_ITALIC)
            if style.get('bold'): pfd.set_weight(pango.WEIGHT_BOLD)
            self.font_styles[name] = pfd

    def run(self):
        self._font_setup()
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
