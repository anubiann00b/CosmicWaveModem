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
        res = (mat_g*np.matrix([ [(freqIndex>>i)&1] for i in reversed(range(4)) ]))%2
        sendByte(sum([res.item(i,0)<<6-i for i in reversed(range(7))]), f)
    f.close()

    return file

def sendByte(val, f):
    #print 'send ', val
    for freqIndex in [(val >> i*2) & 3 for i in reversed(range(4))]:
        appendFrequency(frequencies[freqIndex], f)

def getWaveFile(string, duration=FRAME_TIME):
    file = BytesIO()
    f = wave.open(file, 'w')
    f.setparams((1, 2, BITRATE, len(string)*4*BITRATE*duration, "NONE", "Uncompressed"))
    return f, file

def appendFrequency(freq, f, duration=FRAME_TIME):
    #print 'freq ', freq
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

    maxVal = -1;
    for key, val in dotProducts.iteritems():
        if DEBUG: print key, val
        if val > maxVal: maxVal = val

    if maxVal < 0.3: return None
    return max(dotProducts.iteritems(), key=operator.itemgetter(1))[0]

pairQueue = Queue()

onDecodedDataListener = None
lastNibble = []

def registerOnDecodedDataListener(func):
    global onDecodedDataListener
    onDecodedDataListener = func

def decode(bytes):
    global lastNibble
    matchingFreq = getFreqFromSignal(bytes)
    if matchingFreq is None:
        return None
    print "HANDLING DATA"

    pair = freqBytes[matchingFreq]
    pairQueue.put(pair)

    if pairQueue.qsize() >= 4:
        arr = np.zeros(shape=(7,1))
        for i in range(4):
            val = pairQueue.get()
            if i != 0:
                arr.itemset(i*2-1, 0, (val & 2) >> 1)
            arr.itemset(i*2, 0, val & 1)

        error = (mat_h*arr)%2
        errCol = sum([int(error.item(i,0)) << i for i in range(3)])
        if errCol != 0:
            arr.itemset(errCol-1, 0, 1-arr.item(errCol-1,0))
        message = mat_r*arr

        if len(lastNibble) == 0:
            lastNibble = [message.item(i,0) for i in range(4)]
        else:
            byteArr = []
            byteArr.extend(lastNibble)
            byteArr.extend([message.item(i,0) for i in range(4)])
            lastNibble = []
            onDecodedDataListener(sum([int(byteArr[i]) << i for i in range(8)]))