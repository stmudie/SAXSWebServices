from socketio.namespace import BaseNamespace
from socketio.mixins import BroadcastMixin
import redis
import cPickle as pickle
import os
import xml.etree.ElementTree as ET
#import cElementTree as ET

r = redis.StrictRedis(host='localhost', port=6379, db=1)

class LogViewerNamespace(BaseNamespace, BroadcastMixin):
    
    def initialize(self):
        state = r.get('logviewer:state')
        if state != None:
            self.state = pickle.loads(state)
        else:
            self.state = ''
    
    def find_logfiles(self, ):
        for root, dirs, files in os.walk("/data/pilatus1M/Cycle_2013_3/Law_7085"):
            if 'images' in dirs:
                print 'images'
                index = dirs.index('images')
                del dirs[:index]
                del dirs[1:]
            
            for f in files:
                if os.path.splitext(f)[1] in ['.log']:
                    yield os.path.join(root, f)
    
    def on_state(self, state):
        self.state = state
        r.set('logviewer:state', pickle.dumps(state));
    
    def on_load(self, logfile):
        print 'here'
        with open(logfile, 'r') as f:
            xml_data = f.read()
        xml_data = '<?xml version="1.0" encoding="UTF-8"?><scatterbrain><experiment>'+xml_data+'</experiment></scatterbrain>'
        scatterbrain = ET.XML(xml_data)
        experiment = scatterbrain.find('experiment')
        loglines = experiment.findall('LOGLINE')
        
        keys = []
        files = []
        print 'here1.5'
                
        for logline in loglines:
            keys = keys + logline.keys()
        
        print 'here2'
        # Remove duplicates
        keys = list(set(keys))
            
        data = []   

        for row, logline in enumerate(loglines):
            record = [row,os.path.basename(logline.text)]
            for key in keys:
                record.append(logline.get(key))   
            data.append(record)
                
        self.emit('loadlog', {'keys': keys, 'data' : data, 'state' : self.state})


    def recv_connect(self):
        print 'connect'
        logfiles = [log for log in self.find_logfiles() if (log.find('livelog') >= 0 and log.find('comments') == -1)]
        self.emit('logfiles',logfiles)
    
    def recv_disconnect(self):
        print 'disconnect'

    def recv_message(self, message):
        print "PING!!!", message
