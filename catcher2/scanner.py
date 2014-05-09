import sys
import zmq
from SimpleDaemon import SimpleDaemon
from threading import Thread
from epics import PV, caget, caput
from time import sleep
import cPickle as pickle
import yaml
from Queue import Queue

class Scanner():

    def __init__(self):

        stream = file('config.conf', 'r') 
        config = yaml.load(stream)

        knownscans = config['SCANS']
        
        self.q = Queue()
        
        self.zmqContext = zmq.Context()
        self.pubsubsocket = self.zmqContext.socket(zmq.PUB)
        self.pubsubsocket.bind("tcp://127.0.0.1:5561")

        self.scans = {}
        
        for i, scanname in enumerate(knownscans, start=1):
            self.scans[scanname] = self.PVInits(scanname,knownscans[scanname])
            self.ScanInit(scanname)
            self.scans[scanname]['currentPoint'].add_callback(self.CPTCallback,scanname)
            
      
    def PVInits(self,scanname, scanBasePV):
        
        detActive = ['']*70
        detPVArray = []
        detPVName = []
        
        for i in range(1,71):
            pvarray = '%s.D%02dCA' % (scanBasePV,i)
            pvname = '%s.D%02dPV' % (scanBasePV,i)
            detPVArray.append(PV(pvarray))
            detPVName.append(PV(pvname))
        
        pos1PV = PV(scanBasePV+'.P1PV')
        pos1EGU = PV(scanBasePV+'.P1EU')
        pos1Array = PV(scanBasePV+'.P1CA')

        currentPoint = PV(scanBasePV+'.CPT')
        
        return {'basePV'        : scanBasePV,
                'detActive'     : detActive,
                'detPVArray'    : detPVArray,
                'detPVName'     : detPVName,
                'pos1PV'        : pos1PV,
                'pos1EGU'       : pos1EGU,
                'pos1Array'     : pos1Array,
                'currentPoint'  : currentPoint
               } 
        
        
        
    def ScanInit(self,scanname):
        
        self.pubsubsocket.send_multipart([scanname,pickle.dumps({'message':'NewScan'})])
        self.scans[scanname]['pos1PVVal'] = self.scans[scanname]['pos1PV'].get(use_monitor=False)
        self.scans[scanname]['pos1EGUVal'] = self.scans[scanname]['pos1EGU'].get(use_monitor=False)

        for i,pv in enumerate(self.scans[scanname]['detPVName']):
            self.scans[scanname]['detActive'][i] = pv.get()
        
    def run(self):
        
        print 'starting reqrep thread'
        reqrepthread = Thread(target=self.reqrep)
        reqrepthread.setDaemon(True)
        reqrepthread.start()
        
        
        print 'running'
        while True:
            CPTcallbackDict = self.q.get()
            self.Publish(CPTcallbackDict['cb_info'][0],CPTcallbackDict['value'])
            self.q.task_done()
            sleep(0.1)

    def reqrep(self):
    
        self.reqrepsocket = self.zmqContext.socket(zmq.REP)
        self.reqrepsocket.bind("tcp://127.0.0.1:5560")
    
        while True:
            print 'listening for requests'
            try:
                message = pickle.loads(self.reqrepsocket.recv())
                scanname = message['data']['scanname']
                print scanname
                
                if message['message'] == 'connect':
                    self.reqrepsocket.send(pickle.dumps({'message': 'Scanners','data': self.scans.keys()}))
                
                elif message['message'] == 'profile':
                    cpt = self.scans[scanname]['currentPoint'].get()
                    posdata, detdata = self.getData(scanname,cpt)
                    self.reqrepsocket.send(pickle.dumps({'message':'profile', 'data':{'posdata': posdata, 'detdata': detdata}}))
                
                elif message['message'] == 'positioner':
                    cpt = self.scans[scanname]['currentPoint'].get()
                    print 'here 1'
                    posArray = self.scans[scanname]['pos1Array'].get(use_monitor=False,as_numpy=False)
                    if posArray != None:
                        posArray = posArray[0:cpt]
                    posdata = {'PV':self.scans[scanname]['pos1PVVal'], 'EGU':self.scans[scanname]['pos1EGUVal'], 'Array':posArray}
                    print 'here 2'
                    self.reqrepsocket.send(pickle.dumps({'message':'positioner','data': posdata}))
                
                elif message['message'] == 'activeDet':
                    self.reqrepsocket.send(pickle.dumps({'message':'activeDet','data': self.scans[scanname]['detActive']}))
                
                elif message['message'] == 'detector':
                    cpt = self.scans[scanname]['currentPoint'].get()
                    i = message['data']['detNum']
                    if self.scans[scanname]['detActive'][i] != None:
                        data = self.scans[scanname]['detPVArray'][i].get(use_monitor=False,as_numpy=False)[0:cpt]
                        self.reqrepsocket.send(pickle.dumps({'message':'detector','data': data}))
                    else:
                        self.reqrepsocket.send(pickle.dumps({'message':'detector','data':'Not Active'}))
                    
                elif message['message'] == 'move':
                    print 'move'
                    pv = self.scans[scanname]['pos1PVVal']
                    caput(pv,message['data']['position'])
                    self.reqrepsocket.send(pickle.dumps({'message':'moving'}))
                
                else:
                    pass

            except Exception as e:
                print 'Exception ' + str(e)
                sleep(1)
            
    def getData(self,scanname,cpt):
        
        detdata = {}
     
        for i,pv in enumerate(self.scans[scanname]['detPVArray']):
            detPV = self.scans[scanname]['detActive'][i]
            if detPV != None and detPV != '':
                detdata[detPV] = pv.get(use_monitor=False,as_numpy=False)[0:cpt]
        
        posArray = self.scans[scanname]['pos1Array'].get(use_monitor=False, as_numpy=False)
        if posArray != None:
            posArray = posArray[0:cpt]
                
        posdata = {'PV':self.scans[scanname]['pos1PVVal'], 'EGU':self.scans[scanname]['pos1EGUVal'], 'Array':posArray}

        return posdata, detdata
    
    def CPTCallback(self, pvname, value, cb_info, **kwargs):
        CPTcallbackDict = {'pvname':pvname, 'value':value, 'cb_info':cb_info}
        self.q.put(CPTcallbackDict)
        
    def Publish(self,scanname, cpt):
        print cpt
        if cpt == 0:
            self.ScanInit(scanname)
        
        posdata, detdata = self.getData(scanname,cpt)
        
        self.pubsubsocket.send_multipart([scanname,pickle.dumps({'message':'NewPoint','data':{'posdata': posdata, 'detdata': detdata}})])
            

if __name__ == "__main__":
    a = Scanner()
    a.run()
    while True:
        time.sleep(0.1)
    
    print 'Done'
    
    
    #def ReInit(self):
    #    print 'reiniting'
    #    self.scanBasePV = self.redis.get('scantoredis:scanner')
    #    for pv in self.detPVArray:
    #        try:
    #            pv.disconnect()
    #        except:
    #            print pv
    #    for pv in self.detPVName:
    #        try:
    #            pv.disconnect()
    #        except:
    #            print pv
    #    
    #    try:
    #        self.pos1PV.disconnect()
    #    except:
    #        pass
    #    try:
    #        self.pos1EGU.disconnect()
    #    except:
    #        pass
    #    try:
    #        self.pos1Array.disconnect()
    #    except:
    #        pass
    #    try:
    #        self.currentPoint.disconnect()
    #    except:
    #        pass
    #    
    #    self.PVInits()