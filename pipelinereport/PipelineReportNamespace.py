from socketio.namespace import BaseNamespace
from socketio.mixins import BroadcastMixin
import redis

class PipelineReportNamespace(BaseNamespace, BroadcastMixin):
    def __init__(self, *args, **kwargs):
        super(PipelineReportNamespace,self).__init__(*args,**kwargs)
        
        redisIP,redisdb = self.request['REDIS']['REPORT'].split(':')
        redisdb = int(redisdb)
        self.redis = redis.StrictRedis(host=redisIP, port=6379, db=redisdb)
        
    def sendResultsFromKey(self, key, broadcast=True):

        results = self.redis.hgetall(key)
        filename = key.split(':')[-1]
        if broadcast==True:
            self.broadcast_event('newresults', filename, results)
        else:
            self.emit('newresults', filename, results)

    def checkForNewResult(self):
        while True:
            print 'waiting'
            key = (self.redis.blpop('pipeline:results:queue'))[1]    
            self.sendResultsFromKey(key)

    def recv_connect(self):
        print 'connect'
        numResults = self.redis.zcard('pipeline:results:set')
        resultKeys = self.redis.zrange('pipeline:results:set',0,numResults-1)
        for key in resultKeys:
            if key != 'pipeline:results:queue':            
                self.sendResultsFromKey(key, broadcast=False)

        g = self.spawn(self.checkForNewResult)
    
    def recv_disconnect(self):
        self.kill_local_jobs()
        print 'disconnect'

    def recv_message(self, message):
        print "PING!!!", message