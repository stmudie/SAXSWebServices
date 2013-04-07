from socketio.namespace import BaseNamespace
from socketio.mixins import BroadcastMixin
import redis

r = redis.StrictRedis(host='10.138.11.70', port=6379, db=1)

class PipelineReportNamespace(BaseNamespace, BroadcastMixin):
    def sendResultsFromKey(self, key, broadcast=True):

        results = r.hgetall(key)
        filename = key.split(':')[-1]
        if broadcast==True:
            self.broadcast_event('newresults', filename, results)
        else:
            self.emit('newresults', filename, results)

    def checkForNewResult(self):
        while True:
            print 'waiting'
            key = (r.blpop('pipeline:results:queue'))[1]    
            self.sendResultsFromKey(key)

    def recv_connect(self):
        print 'connect'
        numResults = r.zcard('pipeline:results:set')
        resultKeys = r.zrange('pipeline:results:set',0,numResults-1)
        print resultKeys
        for key in resultKeys:
            if key != 'pipeline:results:queue':            
                self.sendResultsFromKey(key, broadcast=False)

        g = self.spawn(self.checkForNewResult)
    
    def recv_disconnect(self):
        self.kill_local_jobs()
        print 'disconnect'

    def recv_message(self, message):
        print "PING!!!", message