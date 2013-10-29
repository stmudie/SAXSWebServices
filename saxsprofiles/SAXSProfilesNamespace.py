from socketio.namespace import BaseNamespace
from time import sleep, time
from os.path import basename
import cPickle as pickle
import redis

class SAXSProfilesNamespace(BaseNamespace):
    def __init__(self, *args, **kwargs):
        super(SAXSProfilesNamespace,self).__init__(*args,**kwargs)
        
        redisIP,redisdb = self.request['REDIS']['LOG'].split(':')
        redisdb = int(redisdb)
        self.redis = redis.StrictRedis(host=redisIP, port=6379, db=redisdb)
    
    def sendProfile(self, name, data):
        filename = basename(data['filename'])
        fullProfile =[element for element in data['profile'] if element[1]>0]
        self.emit(name, {'filename':filename,'profile':fullProfile})

    def checkForNewRedisProfile(self):
        self.sub = self.redis.pubsub()
        subChannels = self.redis.smembers('logline:channels')
        
        profileNames = [channel.split(':')[-1] for channel in subChannels]
        profiles = self.redis.mget(["logline:%s" % profile for profile in profileNames])
        for profileIndex, profileName in enumerate(profileNames):
            profile = profiles[profileIndex]
            if profile != None :
                data = pickle.loads(profile)
                self.sendProfile(profileName, data)
        
    
        self.sub.subscribe(subChannels)
        zeros = [0]*len(subChannels)
        print 'listening'
        lastTimeSent = dict(zip(subChannels, zeros))
        for message in self.sub.listen():
            print 'Message from channel %s' %(message['channel'],)
            if (message['type'] != 'message'):
                print 'Wrong message type: %s' %(message['type'],)
                continue
            try:
                if time()-lastTimeSent[message['channel']] < 0.5:
                    continue
                data = pickle.loads(message['data'])
                self.sendProfile(message['channel'].split(':')[-1], data)
                lastTimeSent[message['channel']] = time()
            except Exception, e:
                print 'There was an exception in checkForNewRedisProfile: %s' %(e,)

    def recv_connect(self):
        print 'connect'
        g = self.spawn(self.checkForNewRedisProfile)
        
    
    def recv_disconnect(self):
        self.sub.unsubscribe()
        self.kill_local_jobs()
        print 'disconnect'

    def recv_message(self, message):
        print "PING!!!", message