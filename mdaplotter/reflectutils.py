#!/usr/bin/python
from __future__ import division
import numpy as np
import scipy.stats as ss
import scipy.integrate as spi
import os.path as osp

def q(angle, wavelength):
    return 4 * np.pi * np.sin(np.radians(angle)) / wavelength
    
def angle(q, wavelength):
    return np.degrees(np.arcsin(q * wavelength / 4 / np.pi))
    
def wavelength(q, angle):
    return 4 * np.pi * np.sin(np.radians(angle)) / q
    
def qc(sld1, sld2):
    return np.sqrt((sld2 - sld1) * 16 * np.pi)
    
def xraylam(energy):
    #convert energy (keV) to wavelength (angstrom)
    return 12.398/ energy
    
def xrayenergy(wavelength):
    #convert energy (keV) to wavelength (angstrom)
    return 12.398/ wavelength
    
def beamfrac(FWHM, length, angle):
    '''return the beam fraction intercepted by a sample of length length
    at sample tilt angle.
    The beam is assumed to be gaussian, with a FWHM of FWHM.
    '''
    height_of_sample = length * np.sin(np.radians(angle))
    beam_sd = FWHM / 2 / np.sqrt(2 * np.log(2))
    probability = 2. * (ss.norm.cdf(height_of_sample / 2. / beam_sd) - 0.5)
    return probability

def beamfrackernel(kernelx, kernely, length, angle):
    '''return the beam fraction intercepted by a sample of length length
    at sample tilt angle.
    The beam has the shape 'kernel', a 2 row array, which gives the PDF for the beam
    intensity as a function of height. The first row is position, the second row is
    probability at that position
    '''
    height_of_sample = length * np.sin(np.radians(angle))
    total = spi.simps(kernely, kernelx)
    lowlimit = np.where(-height_of_sample / 2. >= kernelx)[0][-1]
    hilimit = np.where(height_of_sample / 2. <= kernelx)[0][0]
    
    area = spi.simps(kernely[lowlimit: hilimit + 1], kernelx[lowlimit: hilimit + 1])
    return area / total
    
def read_SAXSlogs(file, energy = 0, write = True, FWHM = 0.043, length = 200):  
    #reduce synchrotron SAXS reflectivity
    
    with open(file) as f:
        numcolumns = len(f.readline().split(','))
    
    if numcolumns >= 9:
        omega, attenuators, monitor, intensity, energylog    = np.loadtxt(file, delimiter = ',', skiprows = 1, usecols = (0, 2, 5, 6, 8), unpack = True)
    elif numcolumns < 9 and numcolumns > 6:
        omega, attenuators, monitor, intensity    = np.loadtxt(file, delimiter = ',', skiprows = 1, usecols = (0, 2, 5, 6), unpack = True)
    else:
        return
    
    if energy == 0:
        if numcolumns >= 9:
            energy = energylog[0]
        else:
            energy = 11
    
    attenuatorList = np.unique(attenuators)
    
    wavelength = xraylam(energy)
    qq = q(omega, wavelength)
    dintensity = np.sqrt(intensity)
    
    attenuatorList = attenuatorList[::-1]

    for idx, attenuator in enumerate(attenuatorList):
        indices = np.where(attenuators == attenuatorList[idx])[0]
        if idx:
            qtemp = q(omega[indices], wavelength)
            ditemp = np.sqrt(intensity[indices])
            itemp  = intensity[indices] / monitor[indices]
            itemp /= beamfrac(FWHM, length, omega[indices])
            ditemp /= beamfrac(FWHM, length, omega[indices])
            
            scaling, dscaling = get_scaling_in_overlap(totalq, totali, totaldi, qtemp, itemp, ditemp)

            itemp *= scaling
            ditemp *= scaling
            totalq = np.concatenate((totalq, qtemp))
            totali = np.concatenate((totali, itemp))
            totaldi = np.concatenate((totaldi, ditemp)) 
        else:
            totalq = q(omega[indices], wavelength)
            totaldi = np.sqrt(intensity[indices])
            totali = intensity[indices] / monitor[indices]
            totali /= beamfrac(FWHM, length, omega[indices])
            totaldi /= beamfrac(FWHM, length, omega[indices])

    if write:
        fname = 'r_' + osp.basename(file)
        dirname = osp.dirname(file)
        np.savetxt(osp.join(dirname, fname), np.column_stack((totalq, totali, totaldi)))

    return totalq, totali, totaldi

def splicefiles(files, write = True):  
    #splice curves together

    for idx, file in enumerate(files):
        qq, i, di    = np.loadtxt(file, unpack = True)

        if idx:            
            scaling, dscaling = get_scaling_in_overlap(totalq, totali, totaldi, qq, i, di)

            i *= scaling
            di *= scaling
            totalq = np.concatenate((totalq, qq))
            totali = np.concatenate((totali, i))
            totaldi = np.concatenate((totaldi, di)) 
        else:
            totalq = qq
            totali = i
            totaldi = di
            cfname = 'r_' + osp.basename(file)

    if write:
        dirname = osp.dirname(file)
        np.savetxt(osp.join(dirname, cfname), np.column_stack((totalq, totali, totaldi)))

    return totalq, totali, totaldi
    
def get_scaling_in_overlap(qq1,rr1, dr1, qq2, rr2, dr2):
    """
    Get the vertical scaling factor that would splice the second dataset onto the first.
    returns the scaling factor and the uncertainty in scaling factor
    """
    #sort the abscissae
    sortarray = np.argsort(qq1)
    qq1 = qq1[sortarray]
    rr1 = rr1[sortarray]
    dr1 = dr1[sortarray]
    
    sortarray = np.argsort(qq2)
    qq2 = qq2[sortarray]
    rr2 = rr2[sortarray]
    dr2 = dr2[sortarray]
    
    #largest point number of qq2 in overlap region
    num2 = np.interp(qq1[-1:-2:-1], qq2, np.arange(len(qq2) * 1.))
    
    if np.size(num2) == 0:
        return np.NaN, np.NaN
    num2 = int(num2[0])
    
    #get scaling factor at each point of dataset 2 in the overlap region
    #get the intensity of wave1 at an overlap point
    #print qq1.shape, rr1.shape, dr1.shape
    newi = np.interp(qq2[:num2], qq1, rr1)
    newdi = np.interp(qq2[:num2], qq1, dr1)
    
    W_scalefactor = newi / rr2[:num2]
    W_dscalefactor = W_scalefactor * np.sqrt((newdi / newi)**2 + (dr2[:num2] / rr2[:num2])**2)
    W_dscalefactor =  np.sqrt((newdi / rr2[:num2])**2 + ((newi * dr2[:num2])**2) / rr2[:num2]**4)


    W_dscalefactor = 1 / (W_dscalefactor**2)
    
    num = np.sum(W_scalefactor * W_dscalefactor)
    den = np.sum(W_dscalefactor)
 
    normal = num / den
    dnormal = np.sqrt(1/den)

    return normal, dnormal
	
    
def test_beamfrackernel():
    #beam width = 50um
    width = 0.05
    #sample length
    length = 10
    #sample angle
    angle = 0.1
    
    x = np.linspace(-4, 4., 20000.)
    x *= width
    y = ss.norm.pdf(x, scale = width / 2 / np.sqrt(2. * np.log(2.)))
    print beamfrackernel(x, y, length, angle)
    print beamfrac(width, length, angle)
