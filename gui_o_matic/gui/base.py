import copy
import json
import os
import subprocess
import threading
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
        self.next_error_message = None

    def _get_url(self, args, remove=False):
        if isinstance(args, list):
            if remove:
                return args.pop(0), args
            else:
                return args[0], args
        elif isinstance(args, dict):
            url = args['_url']
            if remove:
                del args['_url']
            return url, args
        elif remove:
            return args, None
        else:
            return args, args

    def _do(self, op, args):
        op, args = op.lower(), copy.copy(args)
        try:
            if op == 'show_url':
                url, args = self._get_url(args)
                self.show_url(url=url)

            elif op in ('get_url', 'post_url'):
                url, args = self._get_url(args, remove=True)
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
                for arg in args:
                    rv = os.system(arg)
                    if 0 != rv:
                        raise OSError(
                            'Failed with exit code %d: %s' % (rv, arg))

            elif hasattr(self, op):
                getattr(self, op)(**(args or {}))

        except Exception, e:
            self._report_error(e)

    def _spawn(self, cmd, report_errors=True, _raise=False):
        def waiter(proc):
            try:
                rv = proc.wait()
                if rv:
                    raise Exception('%s returned: %d' % (cmd[0], rv))
            except Exception, e:
                if report_errors:
                    self._report_error(e)
        try:
            proc = subprocess.Popen(cmd, close_fds=True)
            st = threading.Thread(target=waiter, args=[proc])
            st.daemon = True
            st.start()
            return True
        except Exception, e:
            if _raise:
                raise
            elif report_errors:
                self._report_error(e)
        return False

    def set_http_cookie(self, domain=None, key=None, value=None, remove=False):
        all_cookies = self.config.get('http_cookies', {})
        domain_cookies = all_cookies.get(domain, {})
        if remove:
            if key in domain_cookies:
                del domain_cookies[key]
        else:
            domain_cookies[key] = value
            # Ensure the cookie config section exists
            all_cookies[domain] = domain_cookies
            self.config['http_cookies'] = all_cookies

    def terminal(self, command='/bin/bash', title=None, icon=None):
        cmd = [
            "xterm",
            "-T", title or self.config.get('app_name', 'gui-o-matic'),
            "-e", command]
        if icon:
            cmd += ["-n", self._theme_image(icon)]
        self._spawn(cmd)

    def _theme_image(self, path):
        if path.startswith('image:'):
            path = self.config['images'][path.split(':', 1)[1]]
        path = path.replace('%(theme)s', self.ICON_THEME)
        if path != os.path.abspath(path):
            # The protocol mandates absolute paths, to avoid weird breakage
            # if the config and GUI app are generated from different working
            # directories. Fail here to help developers catch bugs early.
            raise ValueError('Path is not absolute: %s' % path)
        return path

    def _add_menu_item(self, id='item', label='Menu item', sensitive=False,
                             op=None, args=None, **ignored_kwargs):
        pass

    def _create_menu_from_config(self):
        menu = self.config.get('indicator', {}).get('menu_items', [])
        for item_info in menu:
            self._add_menu_item(**item_info)

    def set_status(self, status=None, badge=None):
        print('STATUS: %s (badge=%s)' % (status, badge))

    def quit(self):
        raise KeyboardInterrupt("User quit")

    def set_item(self, item=None, label=None, sensitive=None):
        pass

    def set_status_display(self,
            id=None, title=None, details=None, icon=None, color=None):
        pass

    def update_splash_screen(self, message=None, progress=None):
        pass

    def set_next_error_message(self, message=None):
        self.next_error_message = message

    def show_splash_screen(self, height=None, width=None,
                           progress_bar=False, image=None,
                           message=None, message_x=0.5, message_y=0.5):
        pass

    def hide_splash_screen(self):
        pass

    def show_main_window(self):
        pass

    def hide_main_window(self):
        pass

    def show_url(self, url=None):
        assert(url is not None)
        try:
            webbrowser.open(url)
        except Exception, e:
            self._report_error(e)

    def _report_error(self, e):
        traceback.print_exc()
        self.notify_user(
                (self.next_error_message or 'Error: %(error)s')
                % {'error': unicode(e)})

    def notify_user(self,
            message='Hello', popup=False, alert=False, actions=None):
        print('NOTIFY: %s' % message)
