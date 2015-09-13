from scipy.signal import fftconvolve
import numpy as np
from matplotlib.mlab import find
import wave
import math
import struct
from io import BytesIO
import array

DEBUG_DECODE = False

frequencies = [ 350, 375, 400, 425 ]

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

def getWaveFile(string, duration=0.1):
    file = BytesIO()
    f = wave.open(file, 'w')
    f.setparams((1, 2, 8000, len(string)*4*8000*duration, "NONE", "Uncompressed"))
    return f, file

def appendFrequency(freq, f, duration=0.1):
    sampleRate = 8000 # of samples per second (standard)
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

def freq_from_autocorr(sig):
    if DEBUG_DECODE: print
    # Calculate autocorrelation (same thing as convolution, but with 
    # one input reversed in time), and throw away the negative lags
    corr = fftconvolve(sig, sig[::-1], mode='full')
    corr = corr[len(corr)/2:]

    if DEBUG_DECODE: print corr.tolist()
    
    # Find the first low point
    d = np.diff(corr)

    if DEBUG_DECODE: print d.tolist()

    start = find(d > 0)[0]

    start = 3

    if DEBUG_DECODE: print 'strt: ' + str(start)

    # Find the next peak after the low point (other than 0 lag).  This bit is 
    # not reliable for long signals, due to the desired peak occurring between 
    # samples, and other peaks appearing higher.
    # Should use a weighting function to de-emphasize the peaks at longer lags.

    smoothCorr = np.copy(corr)
    for i in range(corr.size):
        if i<2 or i>corr.size-3: continue
        smoothCorr[i] = (corr[i-2] + corr[i-1] + corr[i] + corr[i+1] + corr[i+2])/5

    if DEBUG_DECODE:
        for i in range(400):
            print 'corr: ' + str(smoothCorr[i]/1000000)
            print 'peak: ' + str(i)
            px, py = parabolic(corr, i)
            print '  px:' + str(2*8000/px)
            print

    peak = np.argmax(smoothCorr[start:]) + start

    if DEBUG_DECODE: print 'peak: ' + str(peak)

    px, py = parabolic(corr, peak)
    
    return px

def decode(bytes, bitrate, period):
    return 2*bitrate/freq_from_autocorr(bytes)