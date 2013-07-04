from socketio.namespace import BaseNamespace
from math import exp
from time import sleep, time
from os.path import basename
import cPickle as pickle
import redis
import struct

r= redis.StrictRedis(host='localhost', port=6379, db=0)

class MDAPlotterNamespace(BaseNamespace):
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
            data = []
            try:
                with open(message['data'],'r') as f:
                    for line in f:
                        line = (line.strip()).split(',')
                        data.append(line)
            except Exception:
                continue
            
            
            data = zip(*data)
            
            #Hard coded for reflectivity
            omega = [float(o) for o in (data[0])[1:]]
            counts = [float(c)/exp(0-53*0.0075*float((data[2])[i])) for i,c in enumerate((data[4][1:]),start=1)]
            
            profile = zip(*[omega,counts])
            print profile
            #print omega
            #print counts
            #profile = [omega,counts]
            
            self.sendProfile(basename(message['data']),profile)
            
    def recv_connect(self):
        print 'connected here'
        g = self.spawn(self.checkForNewRedisProfile)
        
    
    def recv_disconnect(self):
        self.sub.unsubscribe()
        self.kill_local_jobs()
        print 'disconnect'

    def recv_message(self, message):
        print "PING!!!", message