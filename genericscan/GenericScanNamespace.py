from socketio.namespace import BaseNamespace
from epics import PV, caput
import cPickle as pickle
import redis
import time

r = redis.StrictRedis(host='localhost', port=6379, db=0)

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

    def run(self,epn,plate,type='all'):
        data = pickle.loads(r.get('well:' + epn + ':plate:' + plate))
        if type == 'all':
            sampleNames = [data['sampleNames'][int(order)] for order in data['sampleOrder'] if data['sampleNames'][int(order)] != ""]
            positions = [1+int(order) for order in data['sampleOrder'] if data['sampleNames'][int(order)] != ""]
            types = [int(data['sampleType'][int(order)]) for order in data['sampleOrder'] if data['sampleNames'][int(order)] != ""]
            washes = [int(data['washType'][int(order)]) for order in data['sampleOrder'] if data['sampleNames'][int(order)] != ""]
            concentration = [float(data['sampleConc'][int(order)]) for order in data['sampleOrder'] if data['sampleNames'][int(order)] != ""]
        
        elif type == 'selected':
            sampleNames = [data['sampleNames'][int(order)] for order in data['sampleOrder'] if data['sampleInclude'][int(order)] == 1 and data['sampleNames'][int(order)] != ""]
            positions = [1+int(order) for order in data['sampleOrder'] if data['sampleInclude'][int(order)] == 1 and data['sampleNames'][int(order)] != ""]
            types = [int(data['sampleType'][int(order)]) for order in data['sampleOrder'] if data['sampleInclude'][int(order)] == 1 and data['sampleNames'][int(order)] != ""]
            washes = [int(data['washType'][int(order)]) for order in data['sampleOrder'] if data['sampleInclude'][int(order)] == 1 and data['sampleNames'][int(order)] != ""]
            concentration = [float(data['sampleConc'][int(order)]) for order in data['sampleOrder'] if data['sampleInclude'][int(order)] == 1 and data['sampleNames'][int(order)] != ""]
    
        sampleNameString = "".join(sampleNames)
        sampleNameLen = [len(name) for name in sampleNames]
        sampleNameCoord = []
        sampleNameCoord.append(0) 
        for i in range(1,len(sampleNameLen)+1):
            sampleNameCoord.append(sampleNameLen[i-1]+sampleNameCoord[i-1])
    
        print len(sampleNameCoord)

        indexPV = "13INDEXARRAY:array"

        # Setup global scan record parameters
        scanPV = 'SR13ID01HU02IOC02:scan1.'
        result = 0
        result += caput(indexPV + ':arrayIndex1',0)
        result += caput(scanPV+'CMND',6)
        result += caput(scanPV+'BSPV','SR13ID01SYR01:SCAN_RECORD_MESSAGE.VAL')
        result += caput(scanPV+'BSCD',0)
        result += caput(scanPV+'ASPV','SR13ID01SYR01:SCAN_RECORD_MESSAGE.VAL')
        result += caput(scanPV+'ASCD',1)
        result += caput(scanPV+'D01PV','SR13ID01SYR01:FULL_SEL_SQ.VAL')
        result += caput(scanPV+'PDLY',2)
        result += caput(scanPV+'DDLY',5)
        if result != 9 :
            print "Something wrong setting " + str(9-result) + " PVs. Continuing anyway."
        
        # Setup positioners for proteins
        result = 0
        positioner = ['SR13ID01SYR01:SMPL_RAW_COORD','SR13ID01SYR01:WASH_TYPE','SR13ID01HU02IOC04:SMPL_TYPE']
        dictKey = ['COORD','WASH','TYPE']
        data = {'COORD': positions, 'WASH': washes, 'TYPE': types}
        for posNum in range(3):
            result += caput(scanPV+'R'+str(1+posNum)+'PV', positioner[posNum])
            result += caput(scanPV+'P'+str(1+posNum)+'PV', positioner[posNum])
            result += caput(scanPV+'P'+str(1+posNum)+'SM', 1)
            time.sleep(0.1)
            result += caput(scanPV+'P'+str(1+posNum)+'PA', data[dictKey[posNum]])
            result += caput(scanPV+'NPTS', len(positions))
        if result != 13 :
            print "Something wrong setting " + str(15-result) + " some PVs. Continuing anyway."
    
        # Setup sample name and concentration positioners
        result = 0
        result += caput(indexPV+'1:arrayValues', str(sampleNameString))
        result += caput(indexPV+'1:arrayIndices', sampleNameCoord)
        result += caput(indexPV+'2:arrayValues', concentration)
        result += caput(indexPV+'2:arrayIndices', range(len(positions)))
        result += caput(scanPV+'P4SM', 0)
        result += caput(scanPV+'P4SP', 0)
        result += caput(scanPV+'P4EP', len(positions)-1)
        result += caput(scanPV+'R4PV', indexPV + ':arrayIndex1')
        result += caput(scanPV+'P4PV', indexPV + ':arrayIndex1')
        result += caput(indexPV+':arrayIndex2',0)
        result += caput(indexPV+':arrayIndex3',0)
        if result != 11 :
            print "Something wrong setting some PVs. Continuing anyway."
 
        # Setup detectors
        result = caput(scanPV+'T1PV', 'SR13ID01SYR01:FULL_SEL_SQ.VAL')
        if result != 1 :
            print "Something wrong setting some PVs. Continuing anyway."
        
        scanning = caput(scanPV+'EXSC', 1)
        
    def on_runall(self,epn,plate):
        self.run(epn, plate, type = 'all')

    def on_runselected(self,epn,plate):
        self.run(epn, plate, type = 'selected')

    def recv_message(self, message):
        print "PING!!!", message
