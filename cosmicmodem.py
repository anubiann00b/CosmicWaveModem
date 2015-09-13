from scipy.signal import fftconvolve
import numpy as np
from matplotlib.mlab import find
import wave
import math
import struct
from io import BytesIO
import array

DEBUG_DECODE = True

frequencies = [ 325, 375, 425, 475 ]

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
    corrs = fftconvolve(sig, sig[::-1], mode='full')
    corrs = corrs[len(corrs)/2:]

    print corrs

    freqCorrs = {}
    for i, freq in enumerate(frequencies):
        lastCorrFreq = 0
        for iCorr, corrScore in enumerate(corrs): # descending
            px, py = parabolic(corrs, iCorr)
            corrFreq = 2*8000/px;
            if corrFreq < freq:
                print lastCorrFreq, corrs[iCorr-1]/1e6
                print corrFreq, corrScore/1e6
                # if freq-corrFreq > lastCorrFreq-freq:
                    # freqCorrs[freq] = corrScore/1e6
                # else:
                    # freqCorrs[freq] = corrs[iCorr-1]/1e6
                freqCorrs[freq] = (corrScore/1e6 + corrs[iCorr-1]/1e6)/2
                break
            lastCorrFreq = corrFreq

    print freqCorrs

    mostCorrFreq = -1
    mostCorr = -1
    for freq, corr in freqCorrs.items():
        if corr > mostCorr:
            mostCorr = corr
            mostCorrFreq = freq
    return mostCorrFreq

def decode(bytes):
    print
    return freq_from_autocorr(bytes)