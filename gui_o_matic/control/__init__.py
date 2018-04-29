import json
import os
import subprocess
import socket
import time
import threading
import traceback
import urllib2
from gui_o_matic.gui.auto import AutoGUI


class GUIPipeControl(threading.Thread):
    OK_GO = 'OK GO'
    OK_LISTEN = 'OK LISTEN'
    OK_LISTEN_TO = 'OK LISTEN TO:'
    OK_LISTEN_TCP = 'OK LISTEN TCP:'
    OK_LISTEN_HTTP = 'OK LISTEN HTTP:'

    def __init__(self, fd, config=None, gui_object=None):
        threading.Thread.__init__(self)
        self.daemon = True
        self.config = config
        self.gui = gui_object
        self.sock = None
        self.fd = fd
        self.child = None
        self.listening = None

    def shell_pivot(self, command):
        self.child = subprocess.Popen(command,
            shell=True,
            close_fds=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE)
        self.fd = self.child.stdout

    def _listen(self):
        self.listening = socket.socket()
        self.listening.bind(('127.0.0.1', 0))
        self.listening.listen(0)
        return str(self.listening.getsockname()[1])

    def _accept(self):
        if self.child is not None:
            self.listening.settimeout(1)
            for count in range(0, 60):
                try:
                    self.sock = self.listening.accept()[0]
                    self.fd = self.sock.makefile()
                    return
                except socket.timeout:
                    if self.child.poll() is not None:
                        raise
        else:
            self.listening.settimeout(60)
            self.sock = self.listening.accept()[0]
            self.fd = self.sock.makefile()

    def shell_tcp_pivot(self, command):
        port = self._listen()
        self.shell_pivot(command.replace('%PORT%', port))
        self._accept()

    def http_tcp_pivot(self, url):
        port = self._listen()
        urllib2.urlopen(url.replace('%PORT%', port)).read()
        self._accept()

    def do_line_magic(self, line, listen):
        try:
            if not line or line.strip() in (self.OK_GO, self.OK_LISTEN):
                return True, self.OK_LISTEN in line

            elif line.startswith(self.OK_LISTEN_TO):
                self.shell_pivot(line[len(self.OK_LISTEN_TO):].strip())
                return True, True

            elif line.startswith(self.OK_LISTEN_TCP):
                self.shell_tcp_pivot(line[len(self.OK_LISTEN_TCP):].strip())
                return True, True

            elif line.startswith(self.OK_LISTEN_HTTP):
                self.http_tcp_pivot(line[len(self.OK_LISTEN_HTTP):].strip())
                return True, True

            else:
                return False, listen
        except Exception, e:
            if self.gui:
                self.gui._report_error(e)
                time.sleep(30)
                raise

    def bootstrap(self, dry_run=False):
        assert(self.config is None)
        assert(self.gui is None)

        listen = False
        config = []
        while True:
            line = self.fd.readline()

            match, listen = self.do_line_magic(line, listen)
            if match:
                break
            else:
                config.append(line.strip())

        self.config = json.loads(''.join(config))
        self.gui = AutoGUI(self.config)
        if not dry_run:
            if listen:
                self.start()
            self.gui.run()

    def do(self, command, kwargs):
        if hasattr(self.gui, command):
            getattr(self.gui, command)(**kwargs)
        else:
            print('Unknown method: %s' % command)

    def run(self):
        try:
            while not self.gui.ready:
                time.sleep(0.1)
            time.sleep(0.1)
            while True:
                try:
                    line = self.fd.readline()
                except IOError:
                    line = None

                if not line:
                    break
                if line:
                    match, lstn = self.do_line_magic(line, None)
                    if not match:
                        try:
                            cmd, args = line.strip().split(' ', 1)
                            args = json.loads(args)
                            self.do(cmd, args)
                        except (ValueError, IndexError, NameError), e:
                            if self.gui:
                                self.gui._report_error(e)
                                time.sleep(30)
                            else:
                                traceback.print_exc()

        except KeyboardInterrupt:
            return
        except:
            traceback.print_exc()
        finally:
            os._exit(0)
