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
import matplotlib.pyplot as mpl
from scipy.optimize import curve_fit

def extend_profile(filename,minval=0.,psimax=1.05,psimin=0.95):
    
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

    p0 = [0.98,100.,prof2.max(),0.]
    sigma = np.sqrt(prof2)
    popt, pcov = curve_fit(lintanh,psi2,prof2-minval,p0=p0,sigma=sigma)
    
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
    
    np.savetxt(filename+'.extpy',np.column_stack((psi4,prof4)),delimiter="\t",fmt='%1.6f')
    
    f, ax = mpl.subplots()
    ax.plot(psi4,prof4)
    ax.plot(psi,prof,'r.')
    ax.set_xlim([psimin,psimax])
    ax.set_ylim([min(prof4.min(),0.),prof2.max()])

    print 'Close figure to continue'
    mpl.show()
    
#    prof5 = np.loadtxt(filename+'.extended')
#    psi5 = prof5[:,0]
#    prof5 = prof5[:,1]
#    ax.plot(psi5,prof5,'g')   
#    ax.set_yscale('log')
    
    return
    
    
def lintanh(x,a,b,c,d):  
    
    t =  1.0 - np.tanh(b*(x-a))
    s =  0.5*c*(1.0+d*(1.0-x))
    
    return np.multiply(s,t)
