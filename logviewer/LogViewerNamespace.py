from socketio.namespace import BaseNamespace
from socketio.mixins import BroadcastMixin
import redis
import cPickle as pickle
import os
#import xml.etree.ElementTree as ET
import xml.etree.cElementTree as ET

r = redis.StrictRedis(host='10.138.11.70', port=6379, db=0)

class LogViewerNamespace(BaseNamespace, BroadcastMixin):
    
    def initialize(self):
        self.loglength = 0
        state = r.get('logviewer:state')
        if state != None:
            self.state = pickle.loads(state)
        else:
            self.state = ''
        print state    
    
    def find_logfiles(self, ):
        for root, dirs, files in os.walk("/data/pilatus1M/Cycle_2013_3/Xie_7069"):
        #for root, dirs, files in os.walk("/home/mudies/code/testdata/"):
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
    
    def load(self, logfile):
        with open(logfile, 'r') as f:
            xml_data = f.read()
        
        xml_data = '<?xml version="1.0" encoding="UTF-8"?><scatterbrain><experiment>'+xml_data+'</experiment></scatterbrain>'
        scatterbrain = ET.XML(xml_data)
        experiment = scatterbrain.find('experiment')
        loglines = experiment.findall('LOGLINE')
        
        keys = []
        files = []
                
        for logline in loglines:
            keys = keys + logline.keys()
        
        # Remove duplicates
        keys = list(set(keys))
            
        data = []   

        for row, logline in enumerate(loglines):
            record = [row,os.path.basename(logline.text)]
            for key in keys:
                record.append(logline.get(key))   
            data.append(record)
                
        self.emit('loadlog', {'keys': keys, 'data' : data, 'state' : self.state})
        self.loglength = len(data)
    
    def on_load(self, logfile):
        if logfile == 'Current':
            self.loadloglines(-1)
            g_rediswatch = self.spawn(self.rediswatch)
        else :
            g_load = self.spawn(self.load,logfile)
        

    def sendloglist(self):
        logfiles = [log for log in self.find_logfiles() if (log.find('livelog') >= 0 and log.find('comments') == -1)]
        print 'emit'
        self.emit('logfiles',logfiles)
    
    def loadloglines(self, num=-1):
        if num==-1:
            num = r.get('logline:num')
        
        if num <= 0:
            return
        
        loglines =[]
        for row in range(self.loglength+1,num+1):
            linedata = r.hgetall('logline:%d' % (row,))
            record = [row,os.path.basename(linedata['ImageLocation'])]
            record = record + [linedata[key] for key in linedata]
            loglines.append(record)
        self.emit('loglines',loglines)
        self.loglength = num
    
    def rediswatch(self):
        self.sub = r.pubsub()
        
        self.sub.subscribe('logfile:pub:logfileupdate')
        print 'listening'
        for message in self.sub.listen():
            print 'Message from channel %s' %(message['channel'],)
            if (message['type'] != 'message'):
                print 'Wrong message type: %s' %(message['type'],)
                continue
            try:
                if message['data'] >= self.loglength :
                    loglines = self.loadloglines(int(message['data']))
                else :
                    self.emit('error','log file lengths incompatible')
            except Exception, e:
                print 'There was an exception in rediswatch: %s' %(e,)
       
    

    def recv_connect(self):
        print 'connect'
        g_log = self.spawn(self.sendloglist)
    
    def recv_disconnect(self):
        print 'disconnect'
        self.kill_local_jobs()

    def recv_message(self, message):
        print "PING!!!", message
