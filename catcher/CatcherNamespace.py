from socketio.namespace import BaseNamespace
from time import sleep, time
import cPickle as pickle
import redis
import numpy as np
from scipy.optimize import minimize
from math import log10, floor

def round_to_n(x,n):
    return round(x, -int(floor(log10(x))) + (n - 1))


class CatcherNamespace(BaseNamespace):
    def __init__(self, *args, **kwargs):
        super(CatcherNamespace,self).__init__(*args,**kwargs)
        
        self.scaletype = 'absolute'
        
        self.scaleoption = {'absolute' : self.absolute, 'fractional' : self.fractional, 'normalised' : self.normalised}
        
        redisIP,redisdb = self.request['REDIS']['WEBSERVER'].split(':')
        redisdb = int(redisdb)
        self.redis = redis.StrictRedis(host=redisIP, port=6379, db=redisdb)

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
                
        
    def sendProfile(self,replot=False):
        pos1 = pickle.loads(self.redis.get('scantoredis:pos1'))
        activeDet = pickle.loads(self.redis.get('scantoredis:detActive'))
        for i,active in enumerate(activeDet, start = 1):
            if active != '':
                data = pickle.loads(self.redis.get('scantoredis:det%02d' % (i,)))
                profile = zip(pos1,self.scaleoption[self.scaletype](data))
                try:
                    minimum = [round_to_n(pos1[data.index(min(data))],3),min(data)]
                    maximum = [round_to_n(pos1[data.index(max(data))],3),max(data)]
                except:
                    minimum = [0,0]
                    maximum = [0,0]
                    
                statistics = {'max': maximum, 'min': minimum}
                self.emit('raw_dat', {'detNum':i,'detPV': active, 'profile':profile, 'replot' : replot if self.scaletype == 'absolute' else True, 'statistics' : statistics})
    
    
    def checkForNewRedisProfile(self):
        self.sub = self.redis.pubsub()
        self.sub.subscribe('scantoredis:message')
        print 'listening'
        for message in self.sub.listen():
            if message['data'] == 'NewScan':
                self.emit('clear')
            elif message['data'] == 'NewPoint':
                self.sendProfile()

    def on_scale(self,type):
        self.scaletype = type
        self.sendProfile(replot=True)
    
    def recv_connect(self):
        print 'connected here'
        self.sendProfile()
        g = self.spawn(self.checkForNewRedisProfile)
        
    def recv_disconnect(self):
        self.sub.unsubscribe()
        self.kill_local_jobs()
        print 'disconnect'

    def recv_message(self, message):
        print "PING!!!", message
