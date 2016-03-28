import copy
import json
import os
import subprocess
import traceback
import urllib
import webbrowser


class BaseGUI(object):
    """
    This is the parent GUI class, which is subclassed by the various
    platform-specific implementations.
    """

    ICON_THEME = 'light'

    def __init__(self, config):
        self.config = config
        self.ready = False
        self._webview = None

    def _do(self, op, args):
        op, args = op.lower(), copy.copy(args)

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

        elif op == "shell":
            try:
                for arg in args:
                    rv = os.system(arg)
                    if 0 != rv:
                        raise OSError(
                            'Failed with exit code %d: %s' % (rv, arg))
            except:
                traceback.print_exc()

        elif hasattr(self, op):
            getattr(self, op)(**(args or {}))

    def terminal(self, command='/bin/bash', title=None, icon=None):
        cmd = [
            "xterm",
            "-T", title or self.config.get('app_name', 'gui-o-matic'),
            "-e", command]
        if icon:
            cmd += ["-n", icon]
        subprocess.Popen(cmd,
            close_fds=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)

    def _theme_image(self, pathname):
        return pathname.replace('%(theme)s', self.ICON_THEME)

    def _add_menu_item(self, item='item', label='Menu item', sensitive=False,
                             op=None, args=None, **ignored_kwargs):
        pass

    def _create_menu_from_config(self):
        menu = self.config.get('indicator', {}).get('menu', [])
        for item_info in menu:
            self._add_menu_item(**item_info)

    def set_status(self, status='startup'):
        print('STATUS: %s' % status)

    def quit(self):
        raise KeyboardInterrupt("User quit")

    def set_item_label(self, item=None, label=None):
        pass

    def set_item_sensitive(self, item=None, sensitive=True):
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
        print('NOTIFY: %s' % message)
