from socketio.namespace import BaseNamespace
from time import sleep, time
from os.path import basename, splitext, dirname
import cPickle as pickle
import redis
from dat import DatFile
import dat

r= redis.StrictRedis(host='10.138.11.70', port=6379, db=0)
#r= redis.StrictRedis(host='localhost', port=6379, db=0)

class SECProfilesNamespace(BaseNamespace):
    def __init__(self, *args, **kwargs):
        super(SECProfilesNamespace,self).__init__(*args,**kwargs)
        self.bufferrange = [-1,-1]
        self.avBufferDat = DatFile()
        self.avSampleDat = DatFile()
        self.activeFile = ''
    
    def sendSAXSProfile(self, name, data):
        filename = basename(data['filename'])
        fullProfile =[element for element in data['profile'] if element[1]>0]
        self.emit(name, {'filename':filename,'profile':fullProfile})
    
    def updateAverageBuffer(self, bufferrange):
        if bufferrange == self.bufferrange:
            return
        
        self.bufferrange = bufferrange
        
        bufferDats = []
        filename = splitext(self.activeFile)[0]
        bufferNames = ['{0}/raw_dat/{1}_{2}.dat'.format(dirname(dirname(filename)),basename(filename),str(num).zfill(4)) for num in range(bufferrange[0],bufferrange[1])]
        
        count = 0
        for name in bufferNames:
            count = count + 1
            try:
                bufferDats.append(DatFile(name))
            except Exception:
                self.emit('ErrorMessage',{'title': "Error", 'message': "Error opening {0}.".format(name)})
            
            if count%10 == 0 or count == len(bufferNames):
                self.emit('Buffer_Load', round(100*count/len(bufferNames),2))
        self.avBufferDat = dat.average(dat.rejection(bufferDats))

    def on_Plotallsample(self, data):
        
        profiles = []
        
        filename = splitext(self.activeFile)[0]
        
        for profileNumber in range(data['range'][0],data['range'][1]):
            if (data['subtract'] == False):
                try:
                    sampleDat = DatFile('{0}/raw_dat/{1}_{2}.dat'.format(dirname(dirname(filename)),basename(filename),str(profileNumber).zfill(4)))
                except Exception:
                   self.emit('ErrorMessage',{'title': "Error", 'message': "Error opening {0}_{1}.dat.".format(basename(filename),str(profileNumber).zfill(4))})
                   continue
                
            else :
                if data['bufferrange'][0] == -1 and data['bufferrange'][1] == -1:
                    try:
                        sampleDat = DatFile('{0}_{1}.dat'.format(filename,str(profileNumber).zfill(4)))
                    except Exception:
                        self.emit('ErrorMessage',{'title': "Error", 'message': "Error opening {0}_{1}.dat.".format(filename,str(profileNumber).zfill(4))})
                        continue
                else :
                    self.updateAverageBuffer(data['bufferrange'])
                    try:
                        sampleDat = dat.subtract(DatFile('{}/raw_dat/{}_{}.dat'.format(dirname(dirname(filename)),basename(filename),str(profileNumber).zfill(4))),self.avBufferDat)
                    except Exception:
                        self.emit('ErrorMessage',{'title': "Error", 'message': "Error opening {0}_{1}.dat.".format(basename(filename),str(profileNumber).zfill(4))})
                        continue
        
            profiles.append({'filename': '{0}_{1}.dat'.format(basename(filename),str(profileNumber).zfill(4)), 'profile': zip(sampleDat.q, sampleDat.intensities, sampleDat.errors)})
                
        self.emit('AllSampleProfiles',profiles)
    
    def on_Load_Profile(self, data):
        
        filename = splitext(self.activeFile)[0]
        profileNumber = data['position']
        
        if (data['subtract'] == False):
            try:
                sampleDat = DatFile('{0}/raw_dat/{1}_{2}.dat'.format(dirname(dirname(filename)),basename(filename),str(profileNumber).zfill(4)))
            except Exception:
                self.emit('ErrorMessage',{'title': "Error", 'message': "Error opening {0}_{1}.dat.".format(basename(filename),str(profileNumber).zfill(4))})
            
        else :
            if data['bufferrange'][0] == -1 and data['bufferrange'][1] == -1:
                    try:
                        sampleDat = DatFile('{0}_{1}.dat'.format(filename,str(profileNumber).zfill(4)))
                    except Exception:
                        self.emit('ErrorMessage',{'title': "Error", 'message': "Error opening {0}_{1}.dat.".format(filename,str(profileNumber).zfill(4))})
                    
            else :
                self.updateAverageBuffer(data['bufferrange'])
                try:
                    sampleDat = dat.subtract(DatFile('{0}/raw_dat/{1}_{2}.dat'.format(dirname(dirname(filename)),basename(filename),str(profileNumber).zfill(4))),self.avBufferDat)
                except Exception:
                    self.emit('ErrorMessage',{'title': "Error", 'message': "Error opening {0}_{1}.dat.".format(basename(filename),str(profileNumber).zfill(4))})
         
        profile = zip(sampleDat.q, sampleDat.intensities, sampleDat.errors)
        self.sendSAXSProfile('Profile',{'filename': filename, 'profile': profile})
    
    
    def on_Average(self, data):
        print 'average'
        
        self.updateAverageBuffer(data['buffer'])

        filename = splitext(self.activeFile)[0]
        sampleDats = []       
        sampleNames = ['{0}/raw_dat/{1}_{2}.dat'.format(dirname(dirname(filename)),basename(filename),str(num).zfill(4)) for num in range(data['sample'][0],data['sample'][1])]
        
        count = 0
        for name in sampleNames:
            count = count + 1
            try:
                sampleDats.append(DatFile(name))
            except Exception:
                self.emit('ErrorMessage',{'title': "Error", 'message': "Error opening {0}.".format(name)})
            
            if count%10 == 0 or count == len(sampleNames):
                self.emit('Sample_Load', round(100*count/len(sampleNames),2))
            
        sampleDat = dat.average(dat.rejection(sampleDats))

        sampleSubDat = dat.subtract(sampleDat, self.avBufferDat)
        self.avSampleDat = sampleSubDat
        
        profile = zip(sampleSubDat.q, sampleSubDat.intensities, sampleSubDat.errors)
        self.sendSAXSProfile('Profile',{'filename': filename, 'profile': profile})
    
    def on_SaveAverage(self, filename):
        print 'save'
        rawfilename = splitext(self.activeFile)[0]
        self.avSampleDat.save('{0}/analysis/{1}.dat'.format(dirname(dirname(rawfilename)),filename))
    
    def sendProfile(self, name, filter_on_quality = 0):
        try:
            data = pickle.loads(r.get('pipeline:sec:{0}:Rg'.format(self.activeFile)))
        except TypeError:
            self.emit('ErrorMessage',{'title': "Error", 'message': "No data in database."})
            return
        
        namedict = {'Rg_Array': 1, 'I0_Array' : 2, 'Quality' : 3, 'HighQ_Array' : 4}
        
        exp = basename(dirname(dirname(self.activeFile)))
        epn = basename(dirname(dirname(dirname(self.activeFile))))

        for n in name:
            array =[(element[0],element[namedict[n]]) for element in data['profiles'] if element[namedict['Quality']] >= 0]
            self.emit(n, {'filename': self.activeFile, 'epn': epn, 'exp':exp, 'profile':array})

    def checkForNewRedisRgProfile(self):
        
        self.sub = r.pubsub()
        self.sub.subscribe('pipeline:sec:pub:Filename')
        print 'listening'
        lastTimeSent = time()
        for message in self.sub.listen():
            print 'Message from pipeline:sec:pub:Filename'
            if (message['type'] != 'message'):
                print 'Wrong message type: %s' %(message['type'],)
                continue
            try:
                if time()-lastTimeSent < 0.5:
                    continue
                if not r.sismember("pipeline:sec:filenames", message['data']):
                    self.updateFileList()
                if message['data'] == self.activeFile:
                    self.sendProfile(['Rg_Array','I0_Array'])
                lastTimeSent = time()
            except Exception, e:
                print 'There was an exception in checkForNewRedisRgProfile: %s' %(e,)

    def on_LoadFile(self, filename):
        self.bufferrange = [-1,-1]
        self.avBufferDat = DatFile()
        self.avSampleDat = DatFile()
        
        self.activeFile = filename
        self.sendProfile(['Rg_Array','I0_Array','HighQ_Array'])
    
    def updateFileList(self, ):
        print 'update'
        self.emit('File_List',list(r.smembers("pipeline:sec:filenames")))
    
    def recv_connect(self):
        print 'connect Rg'
        self.updateFileList()
        g = self.spawn(self.checkForNewRedisRgProfile)
        
    
    def recv_disconnect(self):
        self.sub.unsubscribe()
        self.kill_local_jobs()
        print 'disconnect'

    def recv_message(self, message):
        print "PING!!!", message
