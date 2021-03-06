#!/usr/bin/env python
import os
import sys
sys.path.append(os.getcwd())
import redis
import cPickle as pickle
import time 

try:
    import localconfig as config
except Exception:
    import config

redisIP,redisdb = config.REDIS['WEBSERVER'].split(':')
redisdb = int(redisdb)
rw = redis.StrictRedis(host=redisIP, port=6379, db=redisdb)

def find_logfiles():
    for root, dirs, files in os.walk("/data/pilatus1M/"):
        if 'images' in dirs:
            index = dirs.index('images')
            del dirs[:index]
            del dirs[1:]
            
        for f in files:
            if os.path.splitext(f)[1] in ['.log']:
                yield os.path.join(root, f)

while(1):
    print 'Last run at %s' % (time.ctime(),)
    logfiles = [log for log in find_logfiles() if (log.find('livelog') >= 0 and log.find('comments') == -1)]
    rw.set('logviewer:logfiles',pickle.dumps(logfiles))
    time.sleep(300)
