from socketio.namespace import BaseNamespace
from time import sleep, time
from os.path import basename, splitext, dirname
import cPickle as pickle
import redis
from dat import DatFile
import dat

#r= redis.StrictRedis(host='10.138.11.70', port=6379, db=0)
r= redis.StrictRedis(host='localhost', port=6379, db=0)

class SECProfilesNamespace(BaseNamespace):
    def __init__(self, *args, **kwargs):
        super(SECProfilesNamespace,self).__init__(*args,**kwargs)
        self.bufferrange = [-1,-1]
        self.avBufferDat = DatFile()
        self.avSampleDat = DatFile()
    
    def sendSAXSProfile(self, name, data):
        filename = basename(data['filename'])
        fullProfile =[element for element in data['profile'] if element[1]>0]
        self.emit(name, {'filename':filename,'profile':fullProfile})
    
    def updateAverageBuffer(self, bufferrange):
        print bufferrange
        if bufferrange == self.bufferrange:
            return
        
        self.bufferrange = bufferrange
        
        bufferDats = []
        filename = splitext(r.get('pipeline:sec:filename'))[0]
        bufferNames = ['{}/raw_dat/{}_{}.dat'.format(dirname(dirname(filename)),basename(filename),str(num).zfill(4)) for num in range(bufferrange[0],bufferrange[1])]
        
        count = 0
        for name in bufferNames:
            count = count + 1
            bufferDats.append(DatFile(name))
            if count%10 == 0 or count == len(bufferNames):
                self.emit('Buffer_Load', round(100*count/len(bufferNames),2))
        self.avBufferDat = dat.average(dat.rejection(bufferDats))

    def on_Plotallsample(self, data):
        
        profiles = []
        
        filename = splitext(r.get('pipeline:sec:filename'))[0]
        
        for profileNumber in range(data['range'][0],data['range'][1]):
            if (data['subtract'] == False):
                sampleDat = DatFile('{}/raw_dat/{}_{}.dat'.format(dirname(dirname(filename)),basename(filename),str(profileNumber).zfill(4)))
            else :
                if data['bufferrange'][0] == -1 and data['bufferrange'][1] == -1:
                    sampleDat = DatFile('{}_{}.dat'.format(filename,str(profileNumber).zfill(4)))
                else :
                    self.updateAverageBuffer(data['bufferrange'])
                    sampleDat = dat.subtract(DatFile('{}/raw_dat/{}_{}.dat'.format(dirname(dirname(filename)),basename(filename),str(profileNumber).zfill(4))),self.avBufferDat)
        
            profiles.append({'filename': '{}_{}.dat'.format(basename(filename),str(profileNumber).zfill(4)), 'profile': zip(sampleDat.q, sampleDat.intensities, sampleDat.errors)})
                
        self.emit('AllSampleProfiles',profiles)
    
    def on_Load_Profile(self, data):
        
        filename = splitext(r.get('pipeline:sec:filename'))[0]
        profileNumber = data['position']
        
        if (data['subtract'] == False):
            sampleDat = DatFile('{}/raw_dat/{}_{}.dat'.format(dirname(dirname(filename)),basename(filename),str(profileNumber).zfill(4)))
        else :
            if data['bufferrange'][0] == -1 and data['bufferrange'][1] == -1:
                    sampleDat = DatFile('{}_{}.dat'.format(filename,str(profileNumber).zfill(4)))
            else :
                self.updateAverageBuffer(data['bufferrange'])
                sampleDat = dat.subtract(DatFile('{}/raw_dat/{}_{}.dat'.format(dirname(dirname(filename)),basename(filename),str(profileNumber).zfill(4))),self.avBufferDat)
        
        
        profile = zip(sampleDat.q, sampleDat.intensities, sampleDat.errors)
        self.sendSAXSProfile('Profile',{'filename': filename, 'profile': profile})
    
    
    def on_Average(self, data):
        print 'average'
        
        self.updateAverageBuffer(data['buffer'])

        filename = splitext(r.get('pipeline:sec:filename'))[0]
        sampleDats = []       
        sampleNames = ['{}/raw_dat/{}_{}.dat'.format(dirname(dirname(filename)),basename(filename),str(num).zfill(4)) for num in range(data['sample'][0],data['sample'][1])]
        
        count = 0
        for name in sampleNames:
            count = count + 1
            sampleDats.append(DatFile(name))
            if count%10 == 0 or count == len(sampleNames):
                self.emit('Sample_Load', round(100*count/len(sampleNames),2))
            
        sampleDat = dat.average(dat.rejection(sampleDats))

        sampleSubDat = dat.subtract(sampleDat, self.avBufferDat)
        self.avSampleDat = sampleSubDat
        
        profile = zip(sampleSubDat.q, sampleSubDat.intensities, sampleSubDat.errors)
        self.sendSAXSProfile('Profile',{'filename': filename, 'profile': profile})
    
    def on_SaveAverage(self, filename):
        print 'save'
        rawfilename = splitext(r.get('pipeline:sec:filename'))[0]
        self.avSampleDat.save('{}/analysis/{}.dat'.format(dirname(dirname(rawfilename)),filename))
    
    def sendProfile(self, name, filter_on_quality = 0):
        filename = r.get('pipeline:sec:filename')
        data = pickle.loads(r.get('pipeline:sec:Rg'))
        namedict = {'Rg_Array': 1, 'I0_Array' : 2, 'Quality' : 3, 'HighQ_Array' : 4}
        for n in name:
            array =[(element[0],element[namedict[n]]) for element in data['profiles'] if element[namedict['Quality']] >= 0]
            self.emit(n, {'filename': filename, 'profile':array})

    def checkForNewRedisRgProfile(self):
        
        self.sub = r.pubsub()
        self.sub.subscribe('pipeline:sec:pub:Rg')
        print 'listening'
        lastTimeSent = time()
        for message in self.sub.listen():
            print 'Message from pipeline:sec:pub:Rg'
            if (message['type'] != 'message'):
                print 'Wrong message type: %s' %(message['type'],)
                continue
            try:
                if time()-lastTimeSent < 0.5:
                    continue
                #data = pickle.loads(r.get('pipeline:sec:Rg'))
                self.sendProfile(['Rg_Array','I0_Array'])
                lastTimeSent = time()
            except Exception, e:
                print 'There was an exception in checkForNewRedisRgProfile: %s' %(e,)

    def recv_connect(self):
        print 'connect Rg'
        self.sendProfile(['Rg_Array','I0_Array','HighQ_Array'])
        g = self.spawn(self.checkForNewRedisRgProfile)
        
    
    def recv_disconnect(self):
        self.sub.unsubscribe()
        self.kill_local_jobs()
        print 'disconnect'

    def recv_message(self, message):
        print "PING!!!", message