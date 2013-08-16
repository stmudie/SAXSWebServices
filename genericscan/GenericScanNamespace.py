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
        filenames = []
        
        data = pickle.loads(r.get('generic:' + epn + ':scan:' + scan))
        
        for pos3 in range(0,data['number'][2]):
            for pos2 in range(0,data['number'][1]):
                for pos1 in range(0,data['number'][0]):
                    #position = pos1 + pos2*posData[0].length + pos3*posData[1].length*posData[0].length
                    filenames.append(xstr(data['filenames'][0][pos1]) + xstr(data['filenames'][1][pos2]) + xstr(data['filenames'][2][pos3]))
                    
        filenameString = "".join(filenamess)
        filenameLen = [len(name) for name in filenames]
        
        indexPV = "13INDEXARRAY:array"
        
        # Setup global scan record parameters
        IOCPV = 'SR13ID01HU02IOC02:'
        
        
        result = 0
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
            
            for posNum in range(0,3) :
                absPos = loop*3+posNum
                start = data['start'][absPos]
                end = data['end'][absPos]
                number = data['number'][absPos]
                scantype = data['type'][absPos]
                
                result += caput(scanPV+'R'+str(1+posNum)+'PV', data['positioners'][absPos])
                result += caput(scanPV+'P'+str(1+posNum)+'PV', data['positioners'][absPos])
                
                if scantype == 'Linear':
                    result += caput(scanPV+'P'+str(1+posNum)+'SM', 0)
                    result += caput(scanPV+'P'+str(1+posNum)+'SP', start)
                    result += caput(scanPV+'P'+str(1+posNum)+'EP', end)
                    result += caput(scanPV+'P'+str(1+posNum)+'NPTS', number)
                
                elif scantype == 'Exponential' :
                    prefactor = (end-start)/((number-1)*(step**(number-1)));
                    array = [start + prefactor*i*(step**i) for i in range(number)]
                    result += caput(scanPV+'P'+str(1+posNum)+'SM', 1)
                    result += caput(scanPV+'P'+str(1+posNum)+'PA', array)
                
                elif scantype == 'Table' :
                    result += caput(scanPV+'P'+str(1+posNum)+'SM', 1)
                    result += caput(scanPV+'P'+str(1+posNum)+'PA', data['table'][tableCount])
                    tableCount = tableCount + 1
                    
                else:
                    pass  

        result += caput(indexPV + ':arrayIndex1',0)
        
        
        
        #if result != 9 :
        #    print "Something wrong setting " + str(9-result) + " PVs. Continuing anyway."
        #
        # Setup positioners for proteins
        #result = 0
        #positioner = ['SR13ID01SYR01:SMPL_RAW_COORD','SR13ID01SYR01:WASH_TYPE','SR13ID01HU02IOC04:SMPL_TYPE']
        #dictKey = ['COORD','WASH','TYPE']
        #data = {'COORD': positions, 'WASH': washes, 'TYPE': types}
        #for posNum in range(3):
        #    result += caput(scanPV+'R'+str(1+posNum)+'PV', positioner[posNum])
        #    result += caput(scanPV+'P'+str(1+posNum)+'PV', positioner[posNum])
        #    result += caput(scanPV+'P'+str(1+posNum)+'SM', 1)
        #    time.sleep(0.1)
        #    result += caput(scanPV+'P'+str(1+posNum)+'PA', data[dictKey[posNum]])
        #    result += caput(scanPV+'NPTS', len(positions))
        #if result != 13 :
        #    print "Something wrong setting " + str(15-result) + " some PVs. Continuing anyway."
        #
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
