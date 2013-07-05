from socketio.namespace import BaseNamespace
from math import exp
from time import sleep, time
from os.path import basename, isfile
import cPickle as pickle
import redis
import struct
import reflectutils as ref

r= redis.StrictRedis(host='localhost', port=6379, db=0)

class MDAPlotterNamespace(BaseNamespace):
    def on_filename(self, filename):
        try:
            if isfile(filename) != True:
                return
        except Exception:
            return
        
        self.sendReflectProfile(filename)
    
    def sendReflectProfile(self, filename):
        #Using Andy Nelson's code for reflectivity
        try:
            totalq, totali, totaldi = ref.read_SAXSlogs(filename,write=False)
        except Exception:
            return
        
        profile = [totalq,totali]
        profile = zip(*[totalq,totali])
        self.sendProfile(filename,profile)
    
    def sendProfile(self, filename, data):
        #fullProfile =[element for element in data['profile'] if element[1]>0]
        name = 'raw_dat'
        self.emit(name, {'filename':filename,'profile':data})

    def checkForNewRedisProfile(self):
        self.sub = r.pubsub()
        print 'here'
        self.sub.subscribe('MDA:NewFile')
        print 'listening'
        for message in self.sub.listen():
            print 'New File: %s' %(message,)
            filelist = r.lrange('MDA:reflectivity',0,r.llen('MDA:reflectivity')-1)
            self.emit('file_list',filelist)   #[basename(filename) for filename in filelist])
            if type(message['data']) != str:
                continue
            #data = []
            #try:
            #    with open(message['data'],'r') as f:
            #        for line in f:
            #            line = (line.strip()).split(',')
            #            data.append(line)
            #except Exception:
            #    continue
            #
            #
            #data = zip(*data)
            
            #Hard coded for reflectivity
            #try:
            #    omega = [float(o) for o in (data[0])[1:]]
            #    counts = [float(c)/exp(0-53*0.0075*float((data[2])[i])) for i,c in enumerate((data[6][1:]),start=1)]
            #except Exception:
            #    continue
            #
            #profile = zip(*[omega,counts])
            #print profile
            #self.sendProfile(basename(message['data']),profile)
            self.sendReflectProfile(message['data'])

            
    def recv_connect(self):
        print 'connected here'
        filelist = r.lrange('MDA:reflectivity',0,r.llen('MDA:reflectivity')-1)
        self.emit('file_list',filelist)   #[basename(filename) for filename in filelist])
        g = self.spawn(self.checkForNewRedisProfile)
        
    
    def recv_disconnect(self):
        self.sub.unsubscribe()
        self.kill_local_jobs()
        print 'disconnect'

    def recv_message(self, message):
        print "PING!!!", message
