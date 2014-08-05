from socketio.namespace import BaseNamespace
from epics import PV, caput, caget
import cPickle as pickle
import redis
import time

# Base PVS
indexPV = "13INDEXARRAY:array"
indexPV = "SMTESTINDEX:array"
IOCPV = 'SR13ID01HU02IOC02:'
IOCPV = 'SMTEST:'
triggerPV = '13PIL1:cam1:Acquire'
triggerPV = 'SMTEST:cam1:Acquire'
filenamePV = '13PIL1:cam1:FileName'
filenamePV = 'SMTEST:cam1:FileName'


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
        AVServerIP, AVServerdb = self.request['REDIS']['SOUNDVISIONSERVER'].split(':')
        AVServerdb = int(AVServerdb)
        self.AVServer = redis.StrictRedis(host=AVServerIP, port=6379, db=AVServerdb)
    
        self.scanCPT = [0,0,0]
        self.scanNPTS = [0,0,0]
        self.scanflag = 0
        
        self.scanstarttime = time.time()
        
        scan1PtPV = PV('%sscan%d.CPT' % (IOCPV,1),callback=self.scanupdate)
        scan2PtPV = PV('%sscan%d.CPT' % (IOCPV,2),callback=self.scanupdate)
        scan3PtPV = PV('%sscan%d.CPT' % (IOCPV,3),callback=self.scanupdate)
        
        scan1NPtPV = PV('%sscan%d.NPTS' % (IOCPV,1),callback=self.scanupdate)
        scan2NPtPV = PV('%sscan%d.NPTS' % (IOCPV,2),callback=self.scanupdate)
        scan3NPtPV = PV('%sscan%d.NPTS' % (IOCPV,3),callback=self.scanupdate)
        
        scanRunning = PV('%sscanActive' % (IOCPV,), callback=self.scanupdate)
        
             
    def scanupdate(self, pvname=None, value=None, **kwargs):
        
        elapsedtime = time.time()-self.scanstarttime
        
        if pvname=='%sscanActive' % (IOCPV,):
            if value == 0:
                if self.scanflag >= 1:
                    self.emit('scanstop')
                    try:
		    	if elapsedtime > 30 :
			    self.AVServer.lpush('soundvision:queue','Scan Done#WindowsExclamation2.wav')
                        #elif time.time()-self.scanstarttime > 180:
                        #    self.AVServer.lpush('soundvision:queue','@animal.mp4')
                    except:
                        pass
                
                self.scanflag = 0
                self.playing = 0
            return
        
        pvsplit = pvname.rsplit('.',1)
        pvtype = pvsplit[1]
        scanlevel = int(pvsplit[0][-1:])
        
        if pvtype == 'CPT':
            self.scanCPT[scanlevel-1] = value
            if scanlevel > 1:
                for index in range(scanlevel-1):
                    self.scanCPT[index] = 0
                
        else :
            self.scanNPTS[scanlevel-1] = value
            
        self.emit('scanprogress', {'CPT': self.scanCPT, 'NPTS': self.scanNPTS, 'TopLevel': self.scanflag})
    
        if self.scanflag > 0 and self.playing != 1:
            currentPos = self.scanCPT[0] + (self.scanflag>1)*self.scanCPT[1]*self.scanNPTS[0] + (self.scanflag>2)*self.scanCPT[2]*self.scanNPTS[1]
            totalPos = (self.scanflag==1)*self.scanNPTS[0] + (self.scanflag==2)*self.scanNPTS[1]*self.scanNPTS[0] + (self.scanflag==3)*self.scanNPTS[2]*self.scanNPTS[1]*self.scanNPTS[0]
            timeremain = (totalPos/(float(currentPos)+0.1)-1)*(elapsedtime)
            if timeremain < 40 and elapsedtime + timeremain > 180:
                try:
                    self.AVServer.lpush('soundvision:queue','@animal.mp4')
                    self.playing = 1
                except:
                    pass
            
    
    def on_connect(self):
        print 'connect'
         
        self.emit('beamline', self.request['beamline'])
        self.emit('epn', self.request['epn'][0])
        self.sendlist()

    def on_changeepn(self, user_epn):
        print 'changeepn'
        self.request['epn'][0]=user_epn
        self.emit('epn', self.request['epn'][0])
        scans = list(self.redis.smembers('generic:' + self.request['epn'][0] + ':scans'))
        self.sendlist()

    def on_save(self, data):
        epn = self.request['epn'][0]
        self.redis.sadd('generic:epn', epn)
        self.redis.sadd('generic:' + epn + ':scans', data['scanname'])
        self.redis.set('generic:' + epn + ':scan:' + data['scanname'], pickle.dumps(data))
        scans = list(self.redis.smembers('generic:' + self.request['epn'][0] + ':scans'))
        self.sendlist()
 
    def on_delete(self, epn,scan):
        if epn != self.request['epn'][0]:
            self.emit('message', "You can't delete someone else's scan. Change sharing settings if you don't want to see it.")
        else :
            self.redis.delete('generic:' + epn + ':scan:' + scan)
            self.redis.srem('generic:' + epn + ':scans', scan)
            sharedepns = self.redis.smembers('generic:' + epn + ':scan:' + scan + ':shares')
            self.redis.delete('generic:' + epn + ':scan:' + scan + ':shares')
            for e in sharedepns:
                self.redis.srem('generic:' + e + ':scans', epn +':'+ scan)
            self.sendlist()
 
    def on_load(self, epn, scan):
        print 'on load'
        print epn
        print scan
        redisData = self.redis.get('generic:' + epn + ':scan:' + scan)
        if redisData != None:
            data = pickle.loads(self.redis.get('generic:' + epn + ':scan:' + scan))
        else :
            data = ''

        self.emit('scandata', epn, scan, data)

        shares = self.redis.smembers('generic:' + epn + ':scan:' + scan + ':shares')
        self.emit('shares', list(shares))

    def on_addshare(self, epn, scan, share):
        self.redis.sadd('generic:' + share + ':scans', epn +':'+ scan)
        self.redis.sadd('generic:' + epn + ':scan:' + scan + ':shares', share)
        shares = self.redis.smembers('generic:' + epn + ':scan:' + scan + ':shares')
        self.emit('shares', list(shares))

    def on_deleteshare(self, epn, scan, shares):
        for share in shares:
            self.redis.srem('generic:' + epn + ':scan:' + scan + ':shares', share)
            self.redis.srem('generic:' + share + ':scans', epn +':'+ scan)
        shares = self.redis.smembers('generic:' + epn + ':scan:' + scan + ':shares')
        self.emit('shares', list(shares))

    def on_runsinglepoint(self, positionStruct, name = ''):
        result = 0
        for index,positioner in enumerate(positionStruct['positioner']):
            result += caput(positioner, positionStruct['position'][index], wait = True)
        if (name != ''):
            result += caput(filenamePV, name)
        result += caput(triggerPV, 1)

    def sendlist(self):
        epnscans = []
        beamlinescans = []
        epnscansdict = {self.request['epn'][0]:[]}
        beamlinescansdict = {'Beamline':[]}
        if self.request['epn'][0] != 'Beamline':
            epnscans = list(self.redis.smembers('generic:' + self.request['epn'][0] + ':scans'))
            for scan in epnscans:
                if len(scan.split(':')) == 2:
                    epn,scan = scan.split(':')
                    try:
                        epnscansdict[epn].append(scan)
                    except Exception:
                        epnscansdict[epn]=[scan]
                else:
                    epnscansdict[self.request['epn'][0]].append(scan)
        if self.request['beamline'] != None:
            beamlinescans = list(self.redis.smembers('generic:' + 'Beamline' + ':scans'))
            for scan in beamlinescans:
                if len(scan.split(':')) == 2:
                    epn,scan = scan.split(':')
                    try:
                        beamlinescansdict[epn].append(scan)
                    except Exception:
                        beamlinescansdict[epn]=[scan]
                else:
                    beamlinescansdict['Beamline'].append(scan)
        
        self.emit('loadlist',epnscansdict,beamlinescansdict)
    
    
    def initialise(self,epn,scan,type='all'):
        
        #Load scan data from redis
        data = pickle.loads(self.redis.get('generic:' + epn + ':scan:' + scan))
                
        #Setup filenames
        filenames = []
        #num4 = int(data['number'][(data['nameorder'][3]-1)] or 1)
        #num3 = int(data['number'][(data['nameorder'][2]-1)] or 1)
        #num2 = int(data['number'][(data['nameorder'][1]-1)] or 1)
        #num1 = int(data['number'][(data['nameorder'][0]-1)] or 1)
       
        num4 = int(data['number'][3] or 1)
        num3 = int(data['number'][2] or 1)
        num2 = int(data['number'][1] or 1)
        num1 = int(data['number'][0] or 1)
 
        print data['filenames']

        for pos4 in range(num4):
            for pos3 in range(num3):
                for pos2 in range(num2):
                    for pos1 in range(num1):
                        #position = pos1 + pos2*posData[0].length + pos3*posData[1].length*posData[0].length
                       
                        fragment = []
                        fragment.append(xstr(data['filenames'][0][pos1]))
                        fragment.append(xstr(data['filenames'][1][pos2]))
                        fragment.append(xstr(data['filenames'][2][pos3]))
                        fragment.append(xstr(data['filenames'][3][pos4]))

			filenames.append(fragment[data['nameorder'][0]-1] + fragment[data['nameorder'][1]-1] + fragment[data['nameorder'][2]-1] + fragment[data['nameorder'][3]-1])
#                        filenames.append(xstr(data['filenames'][(data['nameorder'][0]-1)][pos1]) + xstr(data['filenames'][(data['nameorder'][1]-1)][pos2]) + xstr(data['filenames'][(data['nameorder'][2]-1)][pos3]) + xstr(data['filenames'][(data['nameorder'][3]-1)][pos4]))

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
            #if loop == 1 :
            #    result += caput(scanPV+'T1PV',triggerPV)
            #else :
            #    result += caput(scanPV+'T1PV','%sscan%d.EXSC' % (IOCPV,loop-1))
            
            for trig in range(1,5):
                try:
                    result += caput(scanPV+'T'+str(trig)+'PV',data['detTriggers'][(loop-1)*4+trig-1]['PV'])
                except:
                    pass

            #Detectors
            for det in range(1,7):
                try:
                    result += caput(scanPV+'D0'+str(det)+'PV',data['detectors'][(loop-1)*6+det-1]['PV'])
                except:
                    pass
                
            #Set number of points
            number = int(data['number'][loop-1] or 0)
            result += caput(scanPV+'NPTS', number)
            
            #Set Delay
            result += caput(scanPV+'DDLY', int(data['delay'][loop-1] or 0))
            
            #Set Positioner After-Scan Mode (PASM) to PRIOR POS if any positioners relative, otherwise set to STAY
            #This ensures relative scans work correctly
            relative = 'Relative' in data['relative'][(loop-1)*3:(loop)*3]
            result += caput(scanPV+'PASM','PRIOR POS' if relative else 'STAY')
                        
            #Index Array Positioner
            if len(filenameString) > 0:
                result += caput(scanPV+'R4PV', indexPV + ':arrayIndex' + str(loop))
                result += caput(scanPV+'P4PV', indexPV + ':arrayIndex' + str(loop))
                result += caput(scanPV+'P4SM', 0)
                result += caput(scanPV+'P4SP', 0)
                result += caput(scanPV+'P4EP', number-1)            
            
                result += caput(indexPV + ':arrayIndex1',0)
                result += caput(indexPV + ':arrayIndex2',0)
                result += caput(indexPV + ':arrayIndex3',0)
           
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

    def checklimits(self, level):
        time.sleep(0.5) # Make sure scan full initialised, if coming direct from initialise code.
        result = 0
        safe = True
        limitmessages = []
        for l in range(1,level+1):
            result += caput('%sscan%d.CMND' % (IOCPV,l),1,wait = True)
            limitmessages.append(caget('%sscan%d.SMSG' % (IOCPV,l)))
            if limitmessages[-1] != 'SCAN Values within limits':
                safe = False
                                   
        print limitmessages
        self.emit('limitmessage', safe, limitmessages)
        return safe
        
    def run(self, level):
        self.scanflag = level
        self.scanstarttime = time.time()
        self.playing = 0
        scanning = caput('%sscan%d.EXSC' % (IOCPV,level),1)
        if scanning != 1:
            self.scanflag = 0

    def on_initialise(self,epn,scan):
        self.checklimits(self.initialise(epn,scan))
            
    def on_run(self,epn,scan):
        level = self.initialise(epn, scan)
        if self.checklimits(level):
            self.run(level)

    def on_stop(self):
        caput('%sAbortScans.PROC' % (IOCPV,), [1])
        caput('%sAbortScans.PROC' % (IOCPV,), [1])
        caput('%sAbortScans.PROC' % (IOCPV,), [1])
    

    def recv_message(self, message):
        print "PING!!!", message
