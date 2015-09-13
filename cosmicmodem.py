from scipy.signal import fftconvolve
import numpy as np
from matplotlib.mlab import find
import wave
import math
import struct
from io import BytesIO
import array
import operator

DEBUG = True
BITRATE = 8000
FRAMES = 400
FRAME_TIME = float(FRAMES)/BITRATE

frequencies = [ 325, 375, 425, 475 ]
freqBytes = { 325:0, 375:1, 425:2, 475:3 }
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
        for i in range(4):
            yield (c >> i*2) & 3

def encode(string):
    f,file = getWaveFile(string)

    for freqIndex in getFreqs(string):
        print freqIndex
        appendFrequency(frequencies[freqIndex], f)
    f.close()

    return file

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

def decode(bytes):
    return freqBytes[getFreqFromSignal(bytes)]