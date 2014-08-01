import sys
from socketio.namespace import BaseNamespace
from time import sleep, time
import cPickle as pickle
import zmq.green as zmq
import numpy as np
from math import log10, floor
from epics import caput

def round_to_n(x,n):
    return round(x, -int(floor(log10(abs(x)))) + (n - 1))


class Catcher2Namespace(BaseNamespace):
    def __init__(self, *args, **kwargs):
        super(Catcher2Namespace,self).__init__(*args,**kwargs)
        
        #getattr(sys.modules[__name__],'move')
        #for prop, val in vars(sys.modules[__name__]).iteritems():
        #    print prop, ": ", val
        
        self.scaletype = 'absolute'
        self.scaleoption = {'absolute' : self.absolute, 'fractional' : self.fractional, 'normalised' : self.normalised}
        
        reqrepContext = zmq.Context()
        self.reqrepsocket = reqrepContext.socket(zmq.REQ)
        self.reqrepsocket.connect("tcp://127.0.0.1:5560")
        self.reqrepsocket.send(pickle.dumps({'message': 'connect', 'data': {'scanname' : ''}}))
        self.scanners = pickle.loads(self.reqrepsocket.recv())['data']
                
        self.scanner = self.scanners[0]

        publisherContext = zmq.Context()
        self.socketPublisher = publisherContext.socket(zmq.SUB)
        self.socketPublisher.connect("tcp://127.0.0.1:5561")
        

    def __contains__(self,param1):
        return True if param1 in self.__dict__.keys() else False
        
    def absolute(self, profile):
        return profile
    
    def fractional(self, profile):
        if len(profile)==0:
            return profile
        np_profile = np.array(profile)
        np_profile = (np_profile-min(np_profile))/(max(np_profile)-min(np_profile))
        return list(np_profile)

    def normalised(self, profile):
        if len(profile)==0:
            return profile
        np_profile = np.array(profile)
        np_profile = np_profile/max(np_profile)
        return list(np_profile)
                

    def getSendProfile(self,replot=False):
        
        self.reqrepsocket.send(pickle.dumps({'message': 'profile', 'data' : {'scanname' : self.scanner}}))
        message = pickle.loads(self.reqrepsocket.recv())
        
        self.sendProfile(message['data'],replot=replot)
      
    def sendProfile(self,data,replot=False):
      
        pos1Struct = data['posdata']
        pos1temp = pos1Struct['Array']
        pos1 = []
        
        if pos1temp == None:
            print 'return'
            return
        
        for p in pos1temp:
            pos1.append(round_to_n(p,5))

        for i,key in enumerate(data['detdata']):
            data = data['detdata'][key]
            profile = zip(pos1,self.scaleoption[self.scaletype](data))
            try:
                minimum = [round_to_n(pos1[data.index(min(data))],3),min(data)]
                maximum = [round_to_n(pos1[data.index(max(data))],3),max(data)]
            except:
                minimum = [0,0]
                maximum = [0,0]
            statistics = {'max': maximum, 'min': minimum}
            
            self.emit('raw_dat', {'detNum':i,'detPV': key, 'profile':profile, 'replot' : replot if self.scaletype == 'absolute' else True, 'statistics' : statistics})
            
    def initPlot(self):
        self.emit('clear')
        self.emit('scanner')
        
        self.reqrepsocket.send(pickle.dumps({'message': 'positioner', 'data' : {'scanname' : self.scanner}}))
        message = pickle.loads(self.reqrepsocket.recv())
        pos1Struct = message['data']                
        self.emit('positioner',pos1Struct['PV'], pos1Struct['EGU'])

    
    def listen(self):
        print 'listening'
        while True:
            [scanner,message] = self.socketPublisher.recv_multipart()
            message = pickle.loads(message)
            print message['message']
            if message['message'] == 'NewPoint':
                self.sendProfile(message['data'])
            if message['message'] == 'NewScan':
                self.initPlot()
    
                       
    def on_change_scanner(self, scanner):
        if self.scanner != '':
            self.socketPublisher.setsockopt(zmq.UNSUBSCRIBE,str(self.scanner))
        self.socketPublisher.setsockopt(zmq.SUBSCRIBE,str(scanner))
        self.scanner = scanner
        self.initPlot()
        self.getSendProfile()
    
    def on_move(self,pos):
        print 'move'
        self.reqrepsocket.send(pickle.dumps({'message' : 'move', 'data' : {'scanname' : self.scanner, 'position' : pos}}))
        self.reqrepsocket.recv()
    
    def on_scale(self,type):
        self.scaletype = type
        self.getSendProfile(replot=True)
    
    def recv_connect(self):
        print 'connected here'
        self.emit('scanners',self.scanners)
        self.initPlot()
        self.getSendProfile()
        g = self.spawn(self.listen)
        
    def recv_disconnect(self):
        self.kill_local_jobs()
        print 'disconnect all'

    def recv_message(self, message):
        print "PING!!!", message
