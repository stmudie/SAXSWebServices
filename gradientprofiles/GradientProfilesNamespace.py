from socketio.namespace import BaseNamespace
from time import sleep, time
from os.path import basename, splitext, dirname, join, walk, abspath
import untangle
from math import floor
import cPickle as pickle
import redis
import sys
import re
sys.path.append(abspath('../'))
from saxs_auto.dat import DatFile
import saxs_auto.dat as dat
from saxs_auto.offsetsubtract import OffsetSubtract
#from dat import DatFile
#import dat
import urllib2
import fnmatch
from flask import current_app

class GradientProfilesNamespace(BaseNamespace):
    def __init__(self, *args, **kwargs):
        super(GradientProfilesNamespace,self).__init__(*args,**kwargs)
        self.bufferrange = [-1,-1]
        self.saveFilename = ''
        self.logfile = self.request['logfile']
        self.expdir = dirname(dirname(self.request['logfile']))
        self.files = []
        self.suflen = int(self.request['GENERAL']['SUFFIXLENGTH'])
        self.sample_file = ''
        self.buffer_file = ''
        self.sample_high = []
        self.buffer_high = []

    def sendhighqprofile(self, open_file, name, decimate=1):

        highqarray =[]
        filelist = fnmatch.filter(self.files, '%s_????.tif' % (open_file, ))

        for index, filename in enumerate(filelist[::decimate]):
            filename = join(self.expdir, 'raw_dat', splitext(filename)[0] + '.dat')

            try:
                dat = DatFile(filename)
            except (IOError, OSError):
                self.emit('message', {'title': "Error", 'message': "Error opening file %s" % (filename,)})
                continue

            highqarray.append([int(dat.fileindex), dat.highq])
            
        self.emit(name, highqarray)
        return highqarray
    
    def on_openfile(self, sample_file, buffer_file):

        print 'openfile {} {}'.format(sample_file,buffer_file)

        self.sample_file = str(sample_file[0])
        self.buffer_file = str(buffer_file[0])

        decimate = 1

        self.sample_high = self.sendhighqprofile(sample_file[0], "samples", decimate)
        self.buffer_high = self.sendhighqprofile(buffer_file[0], "buffers", decimate)

        slide_range = 50/decimate

        num = len(self.sample_high) - slide_range*2

        sumarray = []
        for shift in range(-slide_range, slide_range):
            sum = 0
            for i in range(num):
                sum = sum + (abs(self.sample_high[slide_range+shift+i][1] - self.buffer_high[slide_range+i][1]))

            sumarray.append(sum)

        self.emit('offset', sumarray.index(min(sumarray))-slide_range)
        self.emit('title', self.sample_file)

    def on_subtract(self, offset, analyse=False):
        # A positive offset means that the buffers graph has been moved negative, as higher buffer indices associated with lower sample indices.
        offset_int = int(floor(offset))
        offset_frac = offset - offset_int
        
        if offset_int >= 0:
            offset_string = 'offset_' + re.sub('\.', 'p', str(offset))
            buff_offset_int = offset_int
            samp_offset_int = 0
        else:
            offset_string = 'offset_minus_' + re.sub('\.', 'p', str(abs(offset)))
            buff_offset_int = 0
            samp_offset_int = abs(offset_int)

        sample_first_num = str(self.sample_high[0][0] + samp_offset_int).zfill(self.suflen)
        buffer_first_num = str(self.buffer_high[0][0] + buff_offset_int).zfill(self.suflen)

        offset_obj = OffsetSubtract()
        try:
            number = offset_obj.subtract(join(self.expdir, 'raw_dat'), '%s_%s.dat' % (self.sample_file, sample_first_num),
                            '%s_%s.dat' % (self.buffer_file, buffer_first_num), offset_frac, join(self.expdir, 'manual', offset_string),
                            join(self.expdir, 'analysis', offset_string), analyse)
        except OSError:
            number = -1
        
        self.emit('finished_sub')
        self.emit('message', {'message': '{} files subtracted.'.format(number), 'title': 'Subtraction Finished'})

    
    def find_raw_profiles(self, ):
        with open(self.logfile, 'r') as f:
            for line in f:
                item = untangle.parse(line).children[0]
                yield str(item.cdata)
        
    def updateFileList(self, ):
        files = []
        self.files = []
        for f in self.find_raw_profiles():
            base = basename(f)
            self.files.append(base)
            files.append(base.rsplit('_', 1)[0])

        seen = set()
        seen_add = seen.add
        files = [[f] for f in files if not (f in seen or seen_add(f))]

        self.emit('File_List', files)
    
    def disconnect(self, silent=False):
        print 'disconnect'
        super(GradientProfilesNamespace, self).disconnect(silent)

    def recv_connect(self, ):
        print 'connect'
        self.updateFileList()

    def recv_disconnect(self):
        print 'force disconnect'
        self.disconnect()

    def recv_message(self, message):
        print "PING!!!", message
