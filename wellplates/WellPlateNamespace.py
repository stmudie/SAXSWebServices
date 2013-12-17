from socketio.namespace import BaseNamespace
from epics import PV, caput
import cPickle as pickle
import redis
import time

class WellPlateNamespace(BaseNamespace):
    def __init__(self, *args, **kwargs):
        super(WellPlateNamespace,self).__init__(*args,**kwargs)
        
        redisIP,redisdb = self.request['REDIS']['WEBSERVER'].split(':')
        redisdb = int(redisdb)
        self.redis = redis.StrictRedis(host=redisIP, port=6379, db=redisdb)
        
    def on_connect(self):
        print 'connect'

        self.emit('beamline', self.request['beamline'])
        self.emit('epn', self.request['epn'][0])
        #plates = list(self.redis.smembers('well:' + self.request['epn'][0] + ':plates'))
        #self.emit('loadlist',plates)
        self.sendlist()

    def on_changeepn(self, user_epn):
        print 'changeepn'
        self.request['epn'][0]=user_epn
        self.emit('epn', self.request['epn'][0])
        #plates = list(self.redis.smembers('well:' + self.request['epn'][0] + ':plates'))
        #self.emit('loadlist',plates)
        self.sendlist()

    def on_save(self, data):
        epn = self.request['epn'][0]
        self.redis.sadd('well:epn', epn)
        self.redis.sadd('well:' + epn + ':plates', data['platename'])
        self.redis.set('well:' + epn + ':plate:' + data['platename'], pickle.dumps(data))
        #plates = list(self.redis.smembers('well:' + self.request['epn'][0] + ':plates'))
        #self.emit('loadlist',plates)
        self.sendlist()
 
    def on_delete(self, epn,plate):
        if epn != self.request['epn'][0]:
            self.emit('message', "You can't delete someone else's plate. Change sharing settings if you don't want to see it.")
        else :
            self.redis.delete('well:' + epn + ':plate:' + plate)
            self.redis.srem('well:' + epn + ':plates', plate)
            sharedepns = self.redis.smembers('well:' + epn + ':plate:' + plate + ':shares')
            self.redis.delete('well:' + epn + ':plate:' + plate + ':shares')
            for e in sharedepns:
                self.redis.srem('well:' + e + ':plates', epn +':'+ plate)
            self.sendlist()
 
    def on_load(self, epn, plate):
        print 'on load'
        redisData = self.redis.get('well:' + epn + ':plate:' + plate)
        if redisData != None:
            data = pickle.loads(self.redis.get('well:' + epn + ':plate:' + plate))
        else :
            data = ''
        
        self.emit('platedata', epn, plate, data)
        
        shares = self.redis.smembers('well:' + epn + ':plate:' + plate + ':shares')
        self.emit('shares', list(shares))

    def on_addshare(self, epn, plate, share):
        self.redis.sadd('well:' + share + ':plates', epn +':'+ plate)
        self.redis.sadd('well:' + epn + ':plate:' + plate + ':shares', share)
        shares = self.redis.smembers('well:' + epn + ':plate:' + plate + ':shares')
        self.emit('shares', list(shares))

    def on_deleteshare(self, epn, plate, shares):
        for share in shares:
            self.redis.srem('well:' + epn + ':plate:' + plate + ':shares', share)
            self.redis.srem('well:' + share + ':plates', epn +':'+ plate)
        shares = self.redis.smembers('well:' + epn + ':plate:' + plate + ':shares')
        self.emit('shares', list(shares))

    def sendlist(self):
        epnplates = []
        beamlineplates = []
        epnplatesdict = {self.request['epn'][0]:[]}
        beamlineplatesdict = {'Beamline':[]}
        if self.request['epn'][0] != 'Beamline':
            epnplates = list(self.redis.smembers('well:' + self.request['epn'][0] + ':plates'))
            for plate in epnplates:
                if len(plate.split(':')) == 2:
                    epn,plate = plate.split(':')
                    try:
                        epnplatesdict[epn].append(plate)
                    except Exception:
                        epnplatesdict[epn]=[plate]
                else:
                    epnplatesdict[self.request['epn'][0]].append(plate)
        if self.request['beamline'] != None:
            beamlineplates = list(self.redis.smembers('well:' + 'Beamline' + ':plates'))
            for plate in beamlineplates:
                if len(plate.split(':')) == 2:
                    epn,plate = plate.split(':')
                    try:
                        beamlineplatesdict[epn].append(plate)
                    except Exception:
                        beamlineplatesdict[epn]=[plate]
                else:
                    beamlineplatesdict['Beamline'].append(plate)
        
        self.emit('loadlist',epnplatesdict,beamlineplatesdict)


    def on_initialise(self,epn,plate,type='all'):
        data = pickle.loads(self.redis.get('well:' + epn + ':plate:' + plate))
        if type == 'all':
            sampleNames = [data['sampleNames'][int(order)] for order in data['sampleOrder'] if data['sampleNames'][int(order)] != ""]
            positions = [1+int(order) for order in data['sampleOrder'] if data['sampleNames'][int(order)] != ""]
            types = [int(data['sampleType'][int(order)]) for order in data['sampleOrder'] if data['sampleNames'][int(order)] != ""]
            washes = [int(data['washType'][int(order)]) for order in data['sampleOrder'] if data['sampleNames'][int(order)] != ""]
            concentration = [float(data['sampleConc'][int(order)]) for order in data['sampleOrder'] if data['sampleNames'][int(order)] != ""]
            molarWeight = [float(data['sampleMW'][int(order)]) for order in data['sampleOrder'] if data['sampleNames'][int(order)] != ""]
        
        
        elif type == 'selected':
            sampleNames = [data['sampleNames'][int(order)] for order in data['sampleOrder'] if data['sampleInclude'][int(order)] == 1 and data['sampleNames'][int(order)] != ""]
            positions = [1+int(order) for order in data['sampleOrder'] if data['sampleInclude'][int(order)] == 1 and data['sampleNames'][int(order)] != ""]
            types = [int(data['sampleType'][int(order)]) for order in data['sampleOrder'] if data['sampleInclude'][int(order)] == 1 and data['sampleNames'][int(order)] != ""]
            washes = [int(data['washType'][int(order)]) for order in data['sampleOrder'] if data['sampleInclude'][int(order)] == 1 and data['sampleNames'][int(order)] != ""]
            concentration = [float(data['sampleConc'][int(order)]) for order in data['sampleOrder'] if data['sampleInclude'][int(order)] == 1 and data['sampleNames'][int(order)] != ""]
            molarWeight = [float(data['sampleMW'][int(order)]) for order in data['sampleOrder'] if data['sampleNames'][int(order)] != ""]
    
    
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
            result += caput(scanPV+'P'+str(1+posNum)+'PA',data[dictKey[posNum]])
            result += caput(scanPV+'NPTS', len(positions))


        if result != 15 :
            print "Something wrong setting " + str(15-result) + " some PVs. Continuing anyway."
    
        # Setup sample name, concentration and molarWeight positioners
        result = 0
        result += caput(indexPV+'1:arrayValues', str(sampleNameString))
        result += caput(indexPV+'1:arrayIndices', sampleNameCoord)
        result += caput(indexPV+'2:arrayValues', concentration)
        result += caput(indexPV+'2:arrayIndices', range(len(positions)))
        result += caput(indexPV+'3:arrayValues', molarWeight)
        result += caput(indexPV+'3:arrayIndices', range(len(positions)))

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

    def run(self):
        scanPV = 'SR13ID01HU02IOC02:scan1.'
        scanning = caput(scanPV+'EXSC', 1)
        
    def on_runall(self,epn,plate):
        self.on_initialise(epn, plate, type = 'all')
        self.run()

    def on_runselected(self,epn,plate):
        self.on_initialise(epn, plate, type = 'selected')
        self.run()

    def recv_message(self, message):
        print "PING!!!", message
