from scipy.signal import fftconvolve
import numpy as np
from matplotlib.mlab import find
import wave
import math
import struct
from io import BytesIO
import array
import operator
from Queue import Queue

DEBUG = True
BITRATE = 8000
FRAMES = 400
FRAME_TIME = float(FRAMES)/BITRATE

mat_g = np.matrix('1 1 0 1; 1 0 1 1; 1 0 0 0; 0 1 1 1; 0 1 0 0; 0 1 0 0; 0 0 0 1')
mat_h = np.matrix('1 0 1 0 1 0 1; 0 1 1 0 0 1 1; 0 0 0 1 1 1 1')
mat_r = np.matrix('0 0 1 0 0 0 0; 0 0 0 0 1 0 0; 0 0 0 0 0 1 0; 0 0 0 0 0 0 1')

frequencies = [ 325, 350, 375, 400, 425, 450, 475, 500 ]
freqBytes = { 325:0, 350:1, 375:2, 400:3, 425:4, 450:5, 475:6, 500:7 }
freqCharts = {
    # 325: {
    #     'sin': [ math.sin(i*2*math.pi*325/8000) for i in range(400) ],
    #     'cos': [ math.sin(i*2*math.pi*325/8000) for i in range(400) ]
    # },
}

def getFunctionsFromFreq(f):
    return {
        'sin': [ math.sin(i*2*math.pi*f/BITRATE) for i in range(FRAMES) ],
        'cos': [ math.sin(i*2*math.pi*f/BITRATE) for i in range(FRAMES) ]
    }

for freq in frequencies:
    freqCharts[freq] = getFunctionsFromFreq(freq)

def getFreqs(string):
    for char in string:
        c = ord(char)
        for i in range(2):
            yield (c >> 4*i) & 15

def encode(string):
    f,file = getWaveFile(string)

    for freqIndex in getFreqs(string):
        res = (mat_g*np.matrix([ [(11>>i)&1] for i in reversed(range(4)) ]))%2
        sendByte(sum([res.item(i,0)<<6-i for i in reversed(range(7))]))
    f.close()

    return file

def sendByte(val):
    for freqIndex in [(val >> i*2) & 3 for i in reversed(range(4))]:
        appendFrequency(frequencies[freqIndex], f)

def getWaveFile(string, duration=FRAME_TIME):
    file = BytesIO()
    f = wave.open(file, 'w')
    f.setparams((1, 2, BITRATE, len(string)*4*BITRATE*duration, "NONE", "Uncompressed"))
    return f, file

def appendFrequency(freq, f, duration=FRAME_TIME):
    sampleRate = BITRATE # of samples per second (standard)
    numChan = 1 # of channels (1: mono, 2: stereo)
    dataSize = 2 # 2 bytes because of using signed short integers => bit depth = 16
    
    data = array.array('h') # signed short integer (-32768 to 32767) data
    numSamplesPerCyc = int(sampleRate / freq)
    numSamples = int(sampleRate * duration)
    for i in range(numSamples):
        sample = 32767 * math.sin(math.pi * 2 * (i % numSamplesPerCyc) / numSamplesPerCyc)
        data.append(int(sample))

    f.writeframes(data.tostring())

# encode("ayla mao")

def parabolic(f, x):
    xv = 1/2. * (f[x-1] - f[x+1]) / (f[x-1] - 2 * f[x] + f[x+1]) + x
    yv = f[x] - 1/4. * (f[x-1] - f[x+1]) * (xv - x)
    return (xv, yv)

def getFreqFromSignal(sig):
    dotProducts = {}
    for freq in frequencies:
        dotProductSin = 0
        dotProductCos = 0
        for i in range(FRAMES):
            dotProductSin += freqCharts[freq]['sin'][i]*(sig[i]/256.0-0.5)
            dotProductCos += freqCharts[freq]['cos'][i]*(sig[i]/256.0-0.5)
        dotProducts[freq] = (dotProductSin*dotProductSin + dotProductCos*dotProductCos)/1e4

    if (DEBUG):
        for key, val in dotProducts.iteritems():
            print key, val

    return max(dotProducts.iteritems(), key=operator.itemgetter(1))[0]

queue = Queue()

def testgetFreqFromSignal(index):
    return [325, 400, 350, 400][index]
    #                 325

def decode(bytes):
    matchingFreq = testgetFreqFromSignal(bytes)

    pair = freqBytes[matchingFreq]
    queue.put(pair)

    if queue.qsize() >= 4:
        arr = np.zeros(shape=(7,1))
        for i in range(4):
            val = queue.get()
            if i != 0:
                arr.itemset(i*2-1, 0, (val & 2) >> 1)
            arr.itemset(i*2, 0, val & 1)

        print arr
        error = (mat_h*arr)%2
        print error
        errCol = sum([int(error.item(i,0)) << i for i in range(3)])
        print errCol
        if errCol != 0:
            arr.itemset(errCol-1, 0, 1-arr.item(errCol-1,0))
        print arr
        message = mat_r*arr
        print message

decode(0)
decode(1)
decode(2)
decode(3)
