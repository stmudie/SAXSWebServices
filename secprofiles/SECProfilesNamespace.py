from socketio.namespace import BaseNamespace
from time import sleep, time
from os.path import basename, splitext, dirname, join, walk
import os
import cPickle as pickle
import redis
from dat import DatFile
import dat
import urllib2
from flask import current_app

class SECProfilesNamespace(BaseNamespace):
    def __init__(self, *args, **kwargs):
        super(SECProfilesNamespace,self).__init__(*args,**kwargs)
        self.bufferrange = [-1,-1]
        self.avBufferDat = DatFile()
        self.avSampleDat = []
        self.activeFile = ''
        self.saveFilename = ''
        self.epn = ''
        self.exp = ''
        #self.pipeurl = 'https://aswebsaxs.synchrotron.org.au/runpipeline'
        self.pipeurl = 'http://127.0.0.1:8082/runpipeline'
        
        redisIP,redisdb = self.request['REDIS']['LOG'].split(':')
        if redisIP == 'No Redis':
            self.redis = 'No Redis'
        else :
            redisdb = int(redisdb)
            self.redis = redis.StrictRedis(host=redisIP, port=6379, db=redisdb)
        
        self.suflen = self.request['GENERAL']['SUFFIXLENGTH']
        
    
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
        filename = (join(dirname(filename),basename(filename).rsplit('_',2)[0]) if self.redis == 'No Redis' else filename)
            
        bufferNames = ['{0}/raw_dat/{1}_{2}.dat'.format(dirname(dirname(filename)),basename(filename),str(num).zfill(self.suflen)) for num in range(bufferrange[0],bufferrange[1])]
        
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
        filename = (join(dirname(filename),basename(filename).rsplit('_',2)[0]) if self.redis == 'No Redis' else filename)
        
        for profileNumber in range(data['range'][0],data['range'][1]):
            if (data['subtract'] == False):
                try:
                    sampleDat = DatFile('{0}/raw_dat/{1}_{2}.dat'.format(dirname(dirname(filename)),basename(filename),str(profileNumber).zfill(self.suflen)))
                except Exception:
                   self.emit('ErrorMessage',{'title': "Error", 'message': "Error opening {0}_{1}.dat.".format(basename(filename),str(profileNumber).zfill(self.suflen))})
                   continue
                
            else :
                if data['bufferrange'][0] == -1 and data['bufferrange'][1] == -1:
                    try:
                        sampleDat = DatFile('{0}_{1}.dat'.format(filename,str(profileNumber).zfill(self.suflen)))
                    except Exception:
                        self.emit('ErrorMessage',{'title': "Error", 'message': "Error opening {0}_{1}.dat.".format(filename,str(profileNumber).zfill(self.suflen))})
                        continue
                else :
                    self.updateAverageBuffer(data['bufferrange'])
                    try:
                        sampleDat = dat.subtract(DatFile('{}/raw_dat/{}_{}.dat'.format(dirname(dirname(filename)),basename(filename),str(profileNumber).zfill(self.suflen))),self.avBufferDat)
                    except Exception:
                        self.emit('ErrorMessage',{'title': "Error", 'message': "Error opening {0}_{1}.dat.".format(basename(filename),str(profileNumber).zfill(self.suflen))})
                        continue
        
            profiles.append({'filename': '{0}_{1}.dat'.format(basename(filename),str(profileNumber).zfill(self.suflen)), 'profile': zip(sampleDat.q, sampleDat.intensities, sampleDat.errors)})
                
        self.emit('AllSampleProfiles',profiles)
    
    def on_Load_Profile(self, data):
        
        filename = splitext(self.activeFile)[0]
        filename = (join(dirname(filename),basename(filename).rsplit('_',2)[0]) if self.redis == 'No Redis' else filename)
                       
        profileNumber = data['position']
        print data['subtract']
                
        if (data['subtract'] == False):
            try:
                sampleDat = DatFile('{0}/raw_dat/{1}_{2}.dat'.format(dirname(dirname(filename)),basename(filename),str(profileNumber).zfill(self.suflen)))
            except Exception:
                self.emit('ErrorMessage',{'title': "Error", 'message': "Error opening {0}_{1}.dat.".format(basename(filename),str(profileNumber).zfill(self.suflen))})
                return
            
        else :
            if data['bufferrange'][0] == -1 and data['bufferrange'][1] == -1:
                    try:
                        sampleDat = DatFile('{0}_{1}.dat'.format(filename,str(profileNumber).zfill(self.suflen)))
                    except Exception:
                        self.emit('ErrorMessage',{'title': "Error", 'message': "Error opening {0}_{1}.dat.".format(filename,str(profileNumber).zfill(self.suflen))})
                        return
                    
            else :
                self.updateAverageBuffer(data['bufferrange'])
                try:
                    sampleDat = dat.subtract(DatFile('{0}/raw_dat/{1}_{2}.dat'.format(dirname(dirname(filename)),basename(filename),str(profileNumber).zfill(self.suflen))),self.avBufferDat)
                except Exception:
                    self.emit('ErrorMessage',{'title': "Error", 'message': "Error opening {0}_{1}.dat.".format(basename(filename),str(profileNumber).zfill(self.suflen))})
                    return
         
        profile = zip(sampleDat.q, sampleDat.intensities, sampleDat.errors)
        self.sendSAXSProfile('Profile',{'filename': filename, 'profile': profile})
    
    
    def on_Average(self, data):
        print 'average'
        
        self.updateAverageBuffer(data['buffer'])

        filename = splitext(self.activeFile)[0]
        filename = (join(dirname(filename),basename(filename).rsplit('_',2)[0]) if self.redis == 'No Redis' else filename)
        averageDats =[]
        sampleDats = []       
        
        for sliceNum in range(data['slices']):
            deltaName = (1+data['sample'][1]-data['sample'][0])/float(data['slices'])
            sampleNames = ['{0}/raw_dat/{1}_{2}.dat'.format(dirname(dirname(filename)),basename(filename),str(num).zfill(self.suflen)) for num in range(data['sample'][0]+int(deltaName*sliceNum),data['sample'][0]+int(deltaName*(sliceNum+1))-1)]
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
            averageDats.append(sampleSubDat)
            
            profile = zip(sampleSubDat.q, sampleSubDat.intensities, sampleSubDat.errors)
            self.sendSAXSProfile('Profile',{'filename': filename, 'profile': profile})
            
        self.avSampleDat = averageDats
        
    
    def on_SaveAverage(self, filename, indexrange):
        print 'save'
        print filename
        self.saveFilename = filename
        rawfilename = splitext(self.activeFile)[0]
        rawfilename = (join(dirname(rawfilename),basename(rawfilename).rsplit('_',2)[0]) if self.redis == 'No Redis' else rawfilename)
        if len(self.avSampleDat) == 1:
            self.avSampleDat[0].save('{0}/manual/{1}'.format(dirname(dirname(rawfilename)),filename))
        else:
            basenamestr = '_'.join(filename.split('.')[0].split('_')[0:-2])
            rangedelta = (1+indexrange[1]-indexrange[0])/float(len(self.avSampleDat))
            slicemin = indexrange[0]
            for num,saveDat in enumerate(self.avSampleDat):
                saveDat.save('{0}/manual/{1}_{2}_{3}.dat'.format(dirname(dirname(rawfilename)),basenamestr,indexrange[0]+int(rangedelta*num),indexrange[0]+int(rangedelta*(num+1))-1))
    
    def on_SendPipeline(self):
        print 'SendPipeline'
        rawfilename = splitext(self.activeFile)[0]
        rawfilename = (join(dirname(rawfilename),basename(rawfilename).rsplit('_',2)[0]) if self.redis == 'No Redis' else rawfilename)
        if len(self.avSampleDat) == 1:
            urllib2.urlopen('{0}/{1}/{2}/manual/{3}.dat'.format(self.pipeurl,self.epn,self.exp,self.saveFilename))
        else:
            for num,saveDat in enumerate(self.avSampleDat):
                urllib2.urlopen('{0}/{1}/{2}/manual/{3}-{4}.dat'.format(self.pipeurl,self.epn,self.exp,self.saveFilename,num))
    
    
    def sendProfile(self, name, filter_on_quality = 0):
        try:
            data = pickle.loads(self.redis.get('pipeline:sec:{0}:Rg'.format(self.activeFile)))
        except AttributeError:
            profile = []
            with open(self.activeFile, 'r') as f:
                next(f)
                for line in f:
                    profile.append(tuple([float(x) for x in line.split()]))
            
            data = {'profiles':profile}
                
        except TypeError:
            self.emit('ErrorMessage',{'title': "Error", 'message': "No data in database."})
            return
        
        namedict = {'Rg_Array': 1, 'I0_Array' : 2, 'Quality' : 3, 'HighQ_Array' : 4}
        
        self.exp = basename(dirname(dirname(self.activeFile)))
        self.epn = basename(dirname(dirname(dirname(self.activeFile))))

        for n in name:
            try:
                array =[(element[0],element[namedict[n]]) for element in data['profiles'] if element[namedict['Quality']] >= 0]
                self.emit(n, {'filename': self.activeFile, 'epn': self.epn, 'exp':self.exp, 'profile':array})
            except IndexError:
                pass
            
    def checkForNewRedisRgProfile(self):
        
        self.sub = self.redis.pubsub()
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
                if not self.redis.sismember("pipeline:sec:filenames", message['data']):
                    self.updateFileList()
                if message['data'] == self.activeFile:
                    self.sendProfile(['Rg_Array','I0_Array'])
                lastTimeSent = time()
            except Exception, e:
                print 'There was an exception in checkForNewRedisRgProfile: %s' %(e,)

    def on_LoadFile(self, filename):
        self.bufferrange = [-1,-1]
        self.avBufferDat = DatFile()
        self.avSampleDat = []
        
        self.activeFile = filename
        self.sendProfile(['Rg_Array','I0_Array','HighQ_Array'])
    
    def find_rg_profiles(self, ):
        #for root, dirs, files in os.walk("/data/pilatus1M/Cycle_2013_3/logfiletest"):
        #for root, dirs, files in os.walk("/home/mudies/code/testdata/"):
        redis,dataPath = self.request['REDIS']['LOG'].split(':')
        print dataPath
        for root, dirs, files in os.walk(dataPath):
            if 'analysis' in dirs:
                print 'analysis'
                index = dirs.index('analysis')
                del dirs[:index]
                del dirs[1:]
            
            for f in files:
                if f.split('_')[-1] == 'rgtrace.dat':
                    yield os.path.join(root, f)
    
    
    def updateFileList(self, ):
        if self.redis == 'No Redis':
            files = [f for f in self.find_rg_profiles()]
        else :
            files = list(self.redis.smembers("pipeline:sec:filenames"))

        self.emit('File_List',files)
    
    def recv_connect(self):
        print 'connect Rg'
        self.updateFileList()
        if self.redis != 'No Redis':
            g = self.spawn(self.checkForNewRedisRgProfile)
        
    
    def recv_disconnect(self):
        if self.redis != "No Redis":
            self.sub.unsubscribe()
            self.kill_local_jobs()
        print 'disconnect'

    def recv_message(self, message):
        print "PING!!!", message
