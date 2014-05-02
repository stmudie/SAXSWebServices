from epics import PV, caget
from time import sleep
import redis
import cPickle as pickle
from threading import Thread

class ScanToRedis():

    def __init__(self):
        
        self.redis = redis.StrictRedis(host='localhost', port=6379, db=0)

        self.scanBasePV = self.redis.get('scantoredis:scanner')
        if self.scanBasePV == None:
            self.scanBasePV = 'SR13ID01HU02IOC02:scan1'
        
        pubsubth = Thread(target=self.Listenscanner)
        pubsubth.start()
        
        self.PVInits()
    
    def ReInit(self):
        print 'reiniting'
        self.scanBasePV = self.redis.get('scantoredis:scanner')
        for pv in self.detPVArray:
            try:
                pv.disconnect()
            except:
                print pv
        for pv in self.detPVName:
            try:
                pv.disconnect()
            except:
                print pv
        
        try:
            self.pos1PV.disconnect()
        except:
            pass
        try:
            self.pos1EGU.disconnect()
        except:
            pass
        try:
            self.pos1Array.disconnect()
        except:
            pass
        try:
            self.currentPoint.disconnect()
        except:
            pass
        
        self.PVInits()
    
    def PVInits(self):
        
        self.detActive = ['']*70
        self.detPVArray = []
        self.detPVName = []
        
        for i in range(1,71):
            pvarray = '%s.D%02dCA' % (self.scanBasePV,i)
            pvname = '%s.D%02dPV' % (self.scanBasePV,i)
            self.detPVArray.append(PV(pvarray))
            self.detPVName.append(PV(pvname))
        
        self.pos1PV = PV(self.scanBasePV+'.P1PV')
        self.pos1EGU = PV(self.scanBasePV+'.P1EU')
        self.pos1Array = PV(self.scanBasePV+'.P1CA')

        self.ScanInit()
        self.currentPoint = PV(self.scanBasePV+'.CPT', callback = self.CPTCallback)
    
    def ScanInit(self):
        self.pos1PVVal = self.pos1PV.get(use_monitor=False)
        self.pos1EGUVal = self.pos1EGU.get(use_monitor=False)
        self.redis.publish('scantoredis:message','NewScan')
        for i,pv in enumerate(self.detPVName):
            self.detActive[i] = pv.get()
    
    def CPTCallback(self, pvname, value, **kwargs):
        th = Thread(target=self.SendToRedis,args=(value,))
        th.start()

    def SendToRedis(self,cpt):
        print 'here'
        if cpt == 0:
            self.ScanInit()
 
        self.redis.set('scantoredis:pos1',pickle.dumps({'PV':self.pos1PVVal, 'EGU':self.pos1EGUVal, 'Array':self.pos1Array.get(use_monitor=False)[0:cpt]}))
        self.redis.set('scantoredis:detActive',pickle.dumps(self.detActive))
        
        for i,pv in enumerate(self.detPVArray):
            if self.detActive[i] != None:
                self.redis.set('scantoredis:det%02d' % (i+1,),pickle.dumps(pv.get(use_monitor=False)[0:cpt]))
    
        self.redis.publish('scantoredis:message','NewPoint')
        
    def Listenscanner(self):
        self.sub = self.redis.pubsub()
        self.sub.subscribe('scantoredis:pub:scannerchange')
        print 'listening'
        for message in self.sub.listen():
            print message
            if self.scanBasePV != self.redis.get('scantoredis:scanner'):
                self.ReInit()

if __name__ == '__main__':
    a = ScanToRedis()
    while True:
        sleep(0.01)
