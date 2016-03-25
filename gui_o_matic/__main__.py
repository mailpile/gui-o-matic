import json
import os
import sys
import time
import threading
import traceback
from gui_o_matic.indicator.auto import AutoIndicator


class StdinWatcher(threading.Thread):
    def __init__(self, config, gui_object):
        threading.Thread.__init__(self)
        self.daemon = True
        self.config = config
        self.gui = gui_object

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
                line = sys.stdin.readline()
                if not line:
                    break
                try:
                    cmd, args = line.strip().split(' ', 1)
                    args = json.loads(args)
                    self.do(cmd, args)
                except (ValueError, IndexError, NameError):
                    traceback.print_exc()
        except:
            traceback.print_exc()
        finally:
            os._exit(0)


indicator, config = None, []
listen = True

while True:
    line = sys.stdin.readline()
    if not line or line.strip() in ('OK LISTEN', 'OK GO'):
        listen = 'LISTEN' in line
        break
    config.append(line.strip())
config = json.loads(''.join(config))

indicator = AutoIndicator(config)
if listen:
    StdinWatcher(config, indicator).start()
indicator.run()
