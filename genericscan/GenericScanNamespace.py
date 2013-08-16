from socketio.namespace import BaseNamespace
from epics import PV, caput
import cPickle as pickle
import redis
import time

r = redis.StrictRedis(host='localhost', port=6379, db=0)

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

class GenericScanNamespace(BaseNamespace):
    def on_connect(self):
        print 'connect'
        self.emit('epn', self.request['epn'][0])
        scans = list(r.smembers('generic:' + self.request['epn'][0] + ':scans'))
        self.emit('loadlist',scans)

    def on_changeepn(self, user_epn):
        print 'changeepn'
        self.request['epn'][0]=user_epn
        self.emit('epn', self.request['epn'][0])
        scans = list(r.smembers('generic:' + self.request['epn'][0] + ':scans'))
        self.emit('loadlist',scans)

    def on_save(self, data):
        epn = self.request['epn'][0]
        r.sadd('generic:epn', epn)
        r.sadd('generic:' + epn + ':scans', data['scanname'])
        r.set('generic:' + epn + ':scan:' + data['scanname'], pickle.dumps(data))
        scans = list(r.smembers('generic:' + self.request['epn'][0] + ':scans'))
        self.emit('loadlist',scans)
 
    def on_load(self, epn, scan):
        print 'on load'
        redisData = r.get('generic:' + epn + ':scan:' + scan)
        if redisData != None:
            data = pickle.loads(r.get('generic:' + epn + ':scan:' + scan))
        else :
            data = ''
        
        self.emit('scandata', epn, scan, data)

    def run(self,epn,scan,type='all'):
        
        #Load scan data from redis
        data = pickle.loads(r.get('generic:' + epn + ':scan:' + scan))
        
        # Base PVS
        indexPV = "13INDEXARRAY:array"
        IOCPV = 'SR13ID01HU02IOC02:'
        result = 0
                
        #Setup filenames
        filenames = []
        num3 = int(data['number'][2] or 1)
        num2 = int(data['number'][1] or 1)
        num1 = int(data['number'][0] or 1)
        
        for pos3 in range(num3):
            for pos2 in range(num2):
                for pos1 in range(num1):
                    #position = pos1 + pos2*posData[0].length + pos3*posData[1].length*posData[0].length
                    filenames.append(xstr(data['filenames'][0][pos1]) + xstr(data['filenames'][1][pos2]) + xstr(data['filenames'][2][pos3]))
                    
        filenameString = "".join(filenames)
        filenameLen = list(running_sum([len(name) for name in filenames]))

        result += caput('%s1:arrayIndices' %(indexPV, ), filenameLen)
        result += caput('%s1:arrayValues' %(indexPV, ), filenameString)

        # Setup global scan record parameters        
        tableCount = 0

        for loop in range(1,4):
            scanPV = 'SR13ID01HU02IOC02:scan%d.' % (loop,)
            
            #Clear SCAN
            result += caput(scanPV+'CMND',3)
            result += caput(scanPV+'PDLY',0)
            
            #Detector Triggers
            if loop == 1 :
                result += caput(scanPV+'T1PV','13PIL1:cam1:Acquire')
            else :
                result += caput(scanPV+'T1PV','SR13ID01HU02IOC02:scan%d.EXSC' % (loop-1,))
            
            #Set number of points
            number = int(data['number'][loop-1] or 0)
            result += caput(scanPV+'NPTS', number)
            
            #Set Delay
            result += caput(scanPV+'DDLY', int(data['delay'][loop-1] or 0))
            
            #Index Array Positioner
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
                
                start = data['start'][absPos]
                end = data['end'][absPos]
                scantype = data['type'][absPos]
                
                result += caput(scanPV+'R'+str(1+posNum)+'PV', data['positioners'][absPos]['PV'])
                result += caput(scanPV+'P'+str(1+posNum)+'PV', data['positioners'][absPos]['PV'])
                
                if scantype == 'Linear':
                    result += caput(scanPV+'P'+str(1+posNum)+'SM', 0)
                    result += caput(scanPV+'P'+str(1+posNum)+'SP', start)
                    result += caput(scanPV+'P'+str(1+posNum)+'EP', end)
                
                elif scantype == 'Exponential' :
                    prefactor = (end-start)/((number-1)*(step**(number-1)));
                    array = [start + prefactor*i*(step**i) for i in range(number)]
                    result += caput(scanPV+'P'+str(1+posNum)+'SM', 1)
                    result += caput(scanPV+'P'+str(1+posNum)+'PA', array)
                
                elif scantype == 'Table' :
                    result += caput(scanPV+'P'+str(1+posNum)+'SM', 1)
                    result += caput(scanPV+'P'+str(1+posNum)+'PA', data['tableData'][tableCount])
                    tableCount = tableCount + 1
                    
                else:
                    pass  

                


        result += caput(indexPV + ':arrayIndex1',0)
        result += caput(indexPV + ':arrayIndex2',0)
        result += caput(indexPV + ':arrayIndex3',0)
        
     
        # Setup sample name and concentration positioners
        #result = 0
        #result += caput(indexPV+'1:arrayValues', str(sampleNameString))
        #result += caput(indexPV+'1:arrayIndices', sampleNameCoord)
        #result += caput(indexPV+'2:arrayValues', concentration)
        #result += caput(indexPV+'2:arrayIndices', range(len(positions)))
        #result += caput(scanPV+'P4SM', 0)
        #result += caput(scanPV+'P4SP', 0)
        #result += caput(scanPV+'P4EP', len(positions)-1)
        #result += caput(scanPV+'R4PV', indexPV + ':arrayIndex1')
        #result += caput(scanPV+'P4PV', indexPV + ':arrayIndex1')
        #result += caput(indexPV+':arrayIndex2',0)
        #result += caput(indexPV+':arrayIndex3',0)
        #if result != 11 :
        #    print "Something wrong setting some PVs. Continuing anyway."
        #
        # Setup detectors
        #result = caput(scanPV+'T1PV', 'SR13ID01SYR01:FULL_SEL_SQ.VAL')
        #if result != 1 :
        #    print "Something wrong setting some PVs. Continuing anyway."
        #
        #scanning = caput(scanPV+'EXSC', 1)
        
    def on_run(self,epn,plate):
        self.run(epn, plate)

    def recv_message(self, message):
        print "PING!!!", message
