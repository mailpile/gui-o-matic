import json
import urllib
import webbrowser


class BaseIndicator(object):
    """
    This is the parent Indicator class, which is subclassed by the various
    platform-specific implementations.
    """

    ICON_THEME = 'light'

    def __init__(self, config):
        self.config = config
        self.ready = False
        self._webview = None

    def _do(self, op, args):
        op, args = op.lower(), args[:]

        if op == 'show_url':
            self.show_url(url=args[0])

        elif op in ('get_url', 'post_url'):
            url = args.pop(0)
            base_url = '/'.join(url.split('/')[:3])

            uo = urllib.URLopener()
            for cookie, value in self.config.get('http_cookies', {}
                                                 ).get(base_url, []):
                uo.addheader('Cookie', '%s=%s' % (cookie, value))

            if op == 'post_url':
                (fn, hdrs) = uo.retrieve(url, data=args)
            else:
                (fn, hdrs) = uo.retrieve(url)
            hdrs = unicode(hdrs)

            with open(fn, 'rb') as fd:
                data = fd.read().strip()

            if data.startswith('{') and 'application/json' in hdrs:
                data = json.loads(data)
                if 'message' in data:
                    self.notify_user(data['message'])

    def _theme_image(self, pathname):
        return pathname.replace('%(theme)s', self.ICON_THEME)

    def _add_menu_item(self, item='item', label='Menu item', sensitive=False,
                             op=None, args=None, **ignored_kwargs):
        pass

    def _create_menu_from_config(self):
        for item_info in self.config.get('indicator_menu', []):
            self._add_menu_item(**item_info)

    def _set_status(self, status):
        print 'STATUS: %s' % status

    def set_status_startup(self):
        self._set_status('startup')

    def set_status_normal(self):
        self._set_status('normal')

    def set_status_working(self):
        self._set_status('working')

    def set_status_attention(self):
        self._set_status('attention')

    def set_status_shutdown(self):
        self._set_status('shutdown')

    def set_menu_label(self, item=None, label=None):
        pass

    def set_menu_sensitive(self, item=None, sensitive=True):
        pass

    def update_splash_screen(self, message=None, progress=None):
        pass

    def show_splash_screen(self, height=None, width=None,
                           progress_bar=False, image=None, message=None):
        pass

    def _get_webview(self):
        return None

    def show_url(self, url=None):
        assert(url is not None)
        if not self.config.get('external_browser'):
            webview = self._get_webview()
            if webview:
                return webview.show_url(url)
        webbrowser.open(url)

    def hide_splash_screen(self):
        pass

    def notify_user(self, message='Hello'):
        print 'NOTIFY: %s' % message
