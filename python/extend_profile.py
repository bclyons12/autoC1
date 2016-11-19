# -*- coding: utf-8 -*-
"""
Reads two columns of data from ASCII file and extends the data by
fitting to the product of linear and tanh functions

filename <string> - Name of the ASCII file
                    The first two columns are assumed to be [psi,prof].
minval <float> -    Asymptotic value of extrapolation at large psi (0.)
psimin <float> -    Minimum psi used to fit data (0.95)
psimax <float> -    Maximum psi to which the data is extrapolated (1.05)

Author:       Brendan Carrick Lyons
Date created: 12/26/15
Date edited:  1/5/16
"""
import math
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

def extend_profile(filename,minval=0.,psimax=1.05,psimin=0.95,center=0.98,
                   width=0.01,smooth=None):
    
    prof = np.loadtxt(filename)
    psi = prof[:,0]
    prof = prof[:,1]
    
    if psimin > psi[-1] :
        print("Error: psimin greater than last psi value defined")
        return
        
    i = np.where(psi>psimin)
    psi2  = psi[i]
    prof2 = prof[i] 
        
    if psimax < psi[-1] :
        print("Error: psimax less than last psi value")
        return
            
    print("Fitting points in range ["+str(psimin)+","+str(psi[-1])+"]")
    print("Fitting to "+str(prof2.size)+" points")

    p0 = [center,1.0/width,prof2.max(),0.]
    sigma = np.sqrt(prof2)
    try:
        popt, pcov = curve_fit(lintanh,psi2,prof2-minval,p0=p0,sigma=sigma)
    except RuntimeError:
        print("Could not fit curve with these parameters")
        f, ax = plt.subplots()
        ax.plot(psi,prof,'r.')
        ax.set_xlim([psimin,psimax])
        plt.waitforbuttonpress(1)
        return
    
    print("Fit center:  " + str(popt[0]))
    print("Fit width:   " + str(1./popt[1]))
    print("Fit height:  " + str(popt[2]))
    print("Fit slope:   " + str(popt[3]))
    
    print("Extending profile to " + str(psimax))
    
    h = psi[-1]-psi[-2]
    
    psi3 = np.arange(psi[-1],psimax,h)
    
    prof3 = lintanh(psi3,popt[0],popt[1],popt[2],popt[3]) + minval
    
    psi4  = np.append(psi,psi3[1:])
    prof4 = np.append(prof,prof3[1:])
    prof5 = lintanh(psi4,popt[0],popt[1],popt[2],popt[3]) + minval
    
    print("Minimum value:  " + str(prof4.min()))
    
    if smooth is not None:
        # smooth profile between smooth and psi[-1]
        imin, pmin = next((i,p) for i,p in enumerate(psi4) if p>smooth)
        imax, pmax = next((i,p) for i,p in enumerate(psi4) if p>psi[-1])
        
#        prmin = prof4[imin]
#        prmax = prof4[imax]
        
        for i in range(imin,imax):
            
            # linear smooth
            #prof4[i] = prmin + (psi4[i]-pmin)*(prmax-prmin)/(pmax-pmin)
    
            # average smooth
            prof4[i] = (psi4[i]-pmin)*prof5[i] +  (pmax-psi4[i])*prof4[i]
            prof4[i] = prof4[i]/(pmax-pmin)
    
    np.savetxt(filename+'.extpy',np.column_stack((psi4,prof4)),delimiter="    ",fmt='%1.6f')
    
    f, ax = plt.subplots()
    ax.plot(psi4,prof5,'g--',linewidth=2)
    ax.plot(psi,prof,'r.',markersize=12)
    ax.plot(psi4,prof4,'b',linewidth=3)
    ax.set_xlim([psimin,psimax])
    ax.set_ylim([min(prof4.min(),0.),prof2.max()])
    if prof4.min()<0.:
        print("Warning: minimum value is negative")
    
    plt.waitforbuttonpress(1)
    
    return
    
def plot_profile(filename,psimin=0.95,ylog=False):
    
    prof = np.loadtxt(filename)
    psi = prof[:,0]
    prof = prof[:,1]
    
    if psimin > psi[-1] :
        print("Error: psimin greater than last psi value defined")
        return
    
    i = np.where(psi>psimin)
    psi2  = psi[i]
    prof2 = prof[i]

    f, ax = plt.subplots()
    ax.plot(psi2,prof2,'r-',linewidth=3)
    minval = prof2.min()
    maxval = prof2.max()
    if ylog:
        ax.set_yscale('log')
        ax.set_ylim([1e-1*minval,maxval])
    else:
        ax.set_ylim([min(minval,0.),maxval])

    plt.show()
    
    return
    
    
def lintanh(x,a,b,c,d):  
    
    t =  1.0 - np.tanh(b*(x-a))
    s =  0.5*c*(1.0+d*(1.0-x))
    
    return np.multiply(s,t)
    
def lintanh2(x,y0,yinf,z,c,w):
    
    A = 1.0 - np.tanh((z-c)/w)
    h = (y0 - yinf + 2.*yinf/A)/z
    
    t = 0.5*(1.0 - np.tanh((x-c)/w))
    s = y0 - yinf - h*x
    
    y = np.multiply(s,t) + yinf

#    y = y - 0.5*(y0 - yinf - 2.0*(y0-ymid)*c)    
    
    return y
    
