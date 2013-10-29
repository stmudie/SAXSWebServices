from socketio.namespace import BaseNamespace
from socketio.mixins import BroadcastMixin
import redis
import cPickle as pickle
import os
#import xml.etree.ElementTree as ET
import xml.etree.cElementTree as ET

class LogViewerNamespace(BaseNamespace, BroadcastMixin):
    def __init__(self, *args, **kwargs):
        super(LogViewerNamespace,self).__init__(*args,**kwargs)
        
        redisIP,redisdb = self.request['REDIS']['LOG'].split(':')
        redisdb = int(redisdb)
        self.redislog = redis.StrictRedis(host=redisIP, port=6379, db=redisdb)
        
        redisIP,redisdb = self.request['REDIS']['WEBSERVER'].split(':')
        redisdb = int(redisdb)
        self.redisweb = redis.StrictRedis(host=redisIP, port=6379, db=redisdb)
        
    def initialize(self):
        self.loglength = 0
        state = self.redisweb.get('logviewer:%s:state' % (self.request['epn'][0]))
        if state != None:
            self.state = pickle.loads(state)
        else:
            self.state = ''
    
    def find_logfiles(self, ):
        for root, dirs, files in os.walk("/data/pilatus1M/Cycle_2013_3/logfiletest"):
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
        self.redisweb.set('logviewer:%s:state' % (self.request['epn'][0],), pickle.dumps(state));
    
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
            record = record + [logline.get(key) if key in logline.keys() else '' for key in keys]
            data.append(record)
                
        self.emit('loadlog', {'keys': keys, 'data' : data, 'state' : self.state})
        self.loglength = len(data)
    
    def on_load(self, logfile):
        self.kill_local_jobs()
        self.loglength = 0
        if logfile == 'Current':
            g_loadloglines = self.spawn(self.loadloglines,-1)
            g_rediswatch = self.spawn(self.rediswatch)
        else :
            g_load = self.spawn(self.load,logfile)
        

    def sendloglist(self):
#        logfiles = [log for log in self.find_logfiles() if (log.find('livelog') >= 0 and log.find('comments') == -1)]
        logfiles = self.redisweb.get('logviewer:logfiles')
        if logfiles != None:
            logfiles = pickle.loads(logfiles)
        else :
            logfiles = ['None Found']
        self.emit('logfiles',logfiles)
    
    def loadloglines(self, num=-1):
        if num==-1:
            num = int(self.redislog.get('logline:num'))
        
        if num <= 0:
            return
        
        rawloglines = []
        for row in range(self.loglength+1,num+1):
            rawloglines.append(self.redislog.hgetall('logline:%d' % (row,)))
            
        keys = list(set([x for keys in rawloglines for x in keys]))

        loglines = []        
        for row, linedata in enumerate(rawloglines):
            record = [self.loglength+row,os.path.basename(linedata['ImageLocation'])]
            record = record + [linedata[key] if key in list(linedata) else '' for key in keys]
            loglines.append(record)

        self.emit('loglines',{'keys': keys, 'data' : loglines, 'state' : self.state})
        self.loglength = num
    
    def rediswatch(self):
        self.sub = self.redislog.pubsub()
        
        self.sub.subscribe('logline:pub:logfileupdate')
        print 'listening'
        for message in self.sub.listen():
            print 'Message from channel %s' %(message['channel'],)
            if (message['type'] != 'message'):
                print 'Wrong message type: %s' %(message['type'],)
                continue
            try:
                if message['data'] >= self.loglength :
                    print 'New line'
                    loglines = self.loadloglines(int(message['data']))
                else :
                    print 'error'
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
