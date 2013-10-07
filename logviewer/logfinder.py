import os
import redis
import cPickle as pickle
import time 
rw = redis.StrictRedis(host='10.138.11.67', port=6379, db=0)

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
