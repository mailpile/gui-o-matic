import json
import os
import subprocess
import socket
import time
import threading
import traceback
from gui_o_matic.gui.auto import AutoGUI


class GUIPipeControl(threading.Thread):
    OK_GO = 'OK GO'
    OK_LISTEN = 'OK LISTEN'
    OK_LISTEN_TO = 'OK LISTEN TO:'
    OK_LISTEN_TCP = 'OK LISTEN TCP:'
    PIVOT_TCP = 'PIVOT TCP:'
    PIVOT_TO = 'PIVOT TO:'

    def __init__(self, fd, config=None, gui_object=None):
        threading.Thread.__init__(self)
        self.daemon = True
        self.config = config
        self.gui = gui_object
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

    def shell_tcp_pivot(self, command):
        self.listening = socket.socket()
        self.listening.bind(('127.0.0.1', 0))
        self.listening.listen(0)
        port = str(self.listening.getsockname()[1])
        self.shell_pivot(command.replace('%PORT%', port))
        self.fd = self.listening.accept()[0].makefile()

    def bootstrap(self):
        assert(self.config is None)
        assert(self.gui is None)

        listen = False
        config = []
        while True:
            line = self.fd.readline()

            if not line or line.strip() in (self.OK_GO, self.OK_LISTEN):
                listen = self.OK_LISTEN in line
                break

            elif line.startswith(self.OK_LISTEN_TO):
                self.shell_pivot(line[len(self.OK_LISTEN_TO):].strip())
                listen = True
                break

            elif line.startswith(self.OK_LISTEN_TCP):
                self.shell_tcp_pivot(line[len(self.OK_LISTEN_TCP):].strip())
                listen = True
                break

            elif line.startswith(self.PIVOT_TCP):
                self.shell_tcp_pivot(line[len(self.PIVOT_TCP):].strip())

            elif line.startswith(self.PIVOT_TO):
                self.shell_pivot(line[len(self.PIVOT_TO):].strip())

            else:
                config.append(line.strip())

        self.config = json.loads(''.join(config))
        self.gui = AutoGUI(self.config)
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
                    if self.listening:
                        self.fd = self.listening.accept()[0].makefile()
                    else:
                        break
                if line:
                    try:
                        cmd, args = line.strip().split(' ', 1)
                        args = json.loads(args)
                        self.do(cmd, args)
                    except (ValueError, IndexError, NameError):
                        traceback.print_exc()
        except KeyboardInterrupt:
            return
        except:
            traceback.print_exc()
        finally:
            os._exit(0)
