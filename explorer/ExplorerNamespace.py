import os
from os.path import join
from socketio.namespace import BaseNamespace
from socketio.mixins import BroadcastMixin

class ExplorerNamespace(BaseNamespace, BroadcastMixin):
    def __init__(self, *args, **kwargs):
        super(ExplorerNamespace, self).__init__(*args, **kwargs)
        self.exp_sub_dirs = ['avg', 'raw_dat', 'raw_sub', 'sub', 'manual', 'analysis']
        self.search_path = "/mnt/san/data/Archive/Cycle_2014_2"

    def find_experiments(self, ):
        print 'finding'
        for root, dirs, files in os.walk(self.search_path):
            dirs_copy = set(dirs)
            dirs[:] = [d for d in dirs if d not in self.exp_sub_dirs + ['images']]
            if {'avg', 'raw_dat', 'raw_sub', 'sub', 'manual', 'analysis'} <= dirs_copy:
                yield(os.path.relpath(root, self.search_path))

    def on_open_experiment(self, experiment):
        experiment = str(experiment[0])
        for dir in self.exp_sub_dirs:
            for root, dirs, files in os.walk(join(self.search_path, experiment, dir)):
                mtime = []
                for f in files:
                    mtime.append(os.path.getmtime(join(self.search_path, experiment, dir, f)))

                self.emit('files', dir, [f for (m, f) in sorted(zip(mtime, files), reverse=True)])

    def recv_connect(self):
        print 'connect'
        self.emit('files', 'experiments', [exp for exp in self.find_experiments()])
        print 'emitted'

    def recv_disconnect(self):
        print 'disconnect'
        self.kill_local_jobs()

    def recv_message(self, message):
        print "PING!!!", message