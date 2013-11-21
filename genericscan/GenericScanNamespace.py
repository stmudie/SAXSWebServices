from socketio.namespace import BaseNamespace
from epics import PV, caput
import cPickle as pickle
import redis
import time

# Base PVS
indexPV = "13INDEXARRAY:array"
#indexPV = "SMTESTINDEX:array"
IOCPV = 'SR13ID01HU02IOC02:'
#IOCPV = 'SMTEST:'

def xstr(s):
    if s is None:
        return ''
    else:
        return s

def running_sum(a):
    tot = 0
    for item in a:
        tot += item
        yield tot

def carefulfloat(a):
    try:
        val = float(a)
    except:
        val = 0

    return val

class GenericScanNamespace(BaseNamespace):
    def __init__(self, *args, **kwargs):
        super(GenericScanNamespace,self).__init__(*args,**kwargs)

        redisIP,redisdb = self.request['REDIS']['WEBSERVER'].split(':')
        redisdb = int(redisdb)
        self.redis = redis.StrictRedis(host=redisIP, port=6379, db=redisdb)
    
    
    def on_connect(self):
        print 'connect'
         
        self.emit('beamline', self.request['beamline'])
        self.emit('epn', self.request['epn'][0])
        scans = list(self.redis.smembers('generic:' + self.request['epn'][0] + ':scans'))
        self.emit('loadlist',scans)

    def on_changeepn(self, user_epn):
        print 'changeepn'
        self.request['epn'][0]=user_epn
        self.emit('epn', self.request['epn'][0])
        scans = list(self.redis.smembers('generic:' + self.request['epn'][0] + ':scans'))
        self.emit('loadlist',scans)

    def on_save(self, data):
        epn = self.request['epn'][0]
        self.redis.sadd('generic:epn', epn)
        self.redis.sadd('generic:' + epn + ':scans', data['scanname'])
        self.redis.set('generic:' + epn + ':scan:' + data['scanname'], pickle.dumps(data))
        scans = list(self.redis.smembers('generic:' + self.request['epn'][0] + ':scans'))
        self.emit('loadlist',scans)
 
    def on_load(self, epn, scan):
        print 'on load'
        redisData = self.redis.get('generic:' + epn + ':scan:' + scan)
        if redisData != None:
            data = pickle.loads(self.redis.get('generic:' + epn + ':scan:' + scan))
        else :
            data = ''
        
        self.emit('scandata', epn, scan, data)

    def initialise(self,epn,scan,type='all'):
        
        #Load scan data from redis
        data = pickle.loads(self.redis.get('generic:' + epn + ':scan:' + scan))
                
        #Setup filenames
        filenames = []
        num4 = int(data['number'][(data['nameorder'][3]-1)] or 1)
        num3 = int(data['number'][(data['nameorder'][2]-1)] or 1)
        num2 = int(data['number'][(data['nameorder'][1]-1)] or 1)
        num1 = int(data['number'][(data['nameorder'][0]-1)] or 1)
        
        for pos4 in range(num4):
            for pos3 in range(num3):
                for pos2 in range(num2):
                    for pos1 in range(num1):
                        #position = pos1 + pos2*posData[0].length + pos3*posData[1].length*posData[0].length
                       
                        filenames.append(xstr(data['filenames'][(data['nameorder'][0]-1)][pos1]) + xstr(data['filenames'][(data['nameorder'][1]-1)][pos2]) + xstr(data['filenames'][(data['nameorder'][2]-1)][pos3]) + xstr(data['filenames'][(data['nameorder'][3]-1)][pos4]))

        filenameString = "".join(filenames)
        filenameLen = list(running_sum([len(name) for name in filenames]))
        filenameLen.insert(0,0)

        result = 0

        if len(filenameString) > 0:
            result += caput('%s1:arrayIndices' %(indexPV, ), filenameLen)
            result += caput('%s1:arrayValues' %(indexPV, ), filenameString)

        # Setup global scan record parameters        
        tableCount = 0

        for loop in range(1,5):
            scanPV = '%sscan%d.' % (IOCPV,loop)
            
            #Clear SCAN
            result += caput(scanPV+'CMND',3)
            result += caput(scanPV+'PDLY',0)
            
            #Detector Triggers
            if loop == 1 :
                result += caput(scanPV+'T1PV','13PIL1:cam1:Acquire')
            else :
                result += caput(scanPV+'T1PV','%sscan%d.EXSC' % (IOCPV,loop-1))
            
            #Set number of points
            number = int(data['number'][loop-1] or 0)
            result += caput(scanPV+'NPTS', number)
            
            #Set Delay
            result += caput(scanPV+'DDLY', int(data['delay'][loop-1] or 0))
            
            #Index Array Positioner
            if len(filenameString) > 0:
                result += caput(scanPV+'R4PV', indexPV + ':arrayIndex' + str(loop))
                result += caput(scanPV+'P4PV', indexPV + ':arrayIndex' + str(loop))
                result += caput(scanPV+'P4SM', 0)
                result += caput(scanPV+'P4SP', 0)
                result += caput(scanPV+'P4EP', number-1)            
            
            for posNum in range(3) :
                absPos = (loop-1)*3+posNum
                
                if not data['positioners'][absPos] :
                    continue
                
                print data['positioners']
                
                try:
	            start =float(data['start'][absPos])
                except:
                    pass

                try:
	            end = float(data['end'][absPos])
                except:
                    pass

                scantype = data['type'][absPos]
                
                result += caput(scanPV+'R'+str(1+posNum)+'PV', data['positioners'][absPos]['PV'])
                result += caput(scanPV+'P'+str(1+posNum)+'PV', data['positioners'][absPos]['PV'])
                result += caput(scanPV+'P'+str(1+posNum)+'AR', data['relative'][absPos]=='Relative')
                
                if scantype == 'Linear':
                    result += caput(scanPV+'P'+str(1+posNum)+'SM', 0)
                    result += caput(scanPV+'P'+str(1+posNum)+'SP', start)
		    result += caput(scanPV+'P'+str(1+posNum)+'EP',end)
                
                elif scantype == 'Exponential' :
                    prefactor = (end-start)/((number-1)*(step**(number-1)));
                    array = [start + prefactor*i*(step**i) for i in range(number)]
                    result += caput(scanPV+'P'+str(1+posNum)+'SM', 1)
                    result += caput(scanPV+'P'+str(1+posNum)+'PA', array)
                
                elif scantype == 'Table' :
                    result += caput(scanPV+'P'+str(1+posNum)+'SM', 1)
                    tableData = [carefulfloat(dataPoint) for dataPoint in (data['tableData'][tableCount])]
                    result += caput(scanPV+'P'+str(1+posNum)+'PA', tableData)
                    tableCount = tableCount + 1
                    
                else:
                    pass  

        result += caput(indexPV + ':arrayIndex1',0)
        result += caput(indexPV + ':arrayIndex2',0)
        result += caput(indexPV + ':arrayIndex3',0)

        #Determine which scan level to start. One less than the lowest with no positions.
        if ((data['number'][0] or 0) > 0):
            level = 1
            if ((data['number'][1] or 0) > 0):
                level = 2
                if ((data['number'][2] or 0) > 0):
                    level = 3
                    if ((data['number'][2] or 0) > 0):
                        level = 4
    
        return level
        
    def run(self, level):
        scanning = caput('%sscan%d.EXSC' % (IOCPV,level), 1)

    def on_initialise(self,epn,scan):
        self.initialise(epn,scan)
    
    def on_run(self,epn,scan):
        self.run(self.initialise(epn, scan))

    def recv_message(self, message):
        print "PING!!!", message
