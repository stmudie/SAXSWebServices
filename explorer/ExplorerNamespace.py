import os
from os.path import join, abspath, splitext
from socketio.namespace import BaseNamespace
from socketio.mixins import BroadcastMixin
import sys
sys.path.append(abspath('../'))
from saxs_auto.dat import DatFile

class ExplorerNamespace(BaseNamespace, BroadcastMixin):
    def __init__(self, *args, **kwargs):
        super(ExplorerNamespace, self).__init__(*args, **kwargs)
        self.exp_sub_dirs = ['avg', 'raw_dat', 'raw_sub', 'sub', 'manual', 'analysis']
        self.search_path = self.request['root_path']

    def find_experiments(self, ):
        print 'finding'
        for root, dirs, files in os.walk(self.search_path):
            dirs_copy = set(dirs)
            dirs[:] = [d for d in dirs if d not in self.exp_sub_dirs]
            
            try:
                dirs.remove('images')
            except ValueError:
                pass
            
            print root
            #if {'avg', 'raw_dat', 'raw_sub', 'sub', 'manual', 'analysis'} <= dirs_copy:
            if any([directory in dirs_copy for directory in self.exp_sub_dirs]):
                del dirs[:]
                yield(os.path.relpath(root, self.search_path))

    def on_open_experiment(self, experiment):
        experiment = str(experiment[0])
        self.experiment = experiment
        for dir in self.exp_sub_dirs:
            try:
                files = next(os.walk(join(self.search_path, experiment, dir)))[2]
                files = [f for f in files if splitext(f)[-1] == '.dat']
            except StopIteration:
                continue
                
            mtime = []
            for f in files:
                mtime.append(os.path.getmtime(join(self.search_path, experiment, dir, f)))

            self.emit('files', dir, [f for (m, f) in sorted(zip(mtime, files), reverse=True)])
        
        self.emit('files', 'finished', [])

    def on_load_dat(self, dat_file, directory):
        #dat_file = str(dat_file)
        print dat_file
        if type(dat_file) is str or type(dat_file) is unicode:
            dat_file = [dat_file]
        directory = str(directory)
        data = []
        for f in dat_file:
            f = str(f)
            d = DatFile(join(self.search_path, self.experiment, directory, f))
            data.append({'name': d.basename_rmext, 'data': zip(d.logbinq(200), d.logbinintensities(200))})
        
        self.emit('data', data)
    
    def recv_connect(self):
        print 'connect'
        self.emit('files', 'experiments', [exp for exp in self.find_experiments()])
        print 'emitted'

    def recv_disconnect(self):
        print 'disconnect'
        self.kill_local_jobs()

    def recv_message(self, message):
        print "PING!!!", message