# -*- coding: utf-8 -*-
"""
Created on Tue Apr 12 14:29:38 2016

@author: lyonsbc
"""

import numpy as np
from my_shutil import mv

def mod_C1input(C1inputs=None,folder='.',append=True):
    
    if C1inputs is None:
        return

    print('Modifying C1input file')
    
    C1copy = C1inputs.copy()
    
    new = folder + '/C1input'
    old = folder + '/C1input.old'
    mv(new,old)
    
    if 'feedback' in C1copy:
        fb_fac = float(C1copy['feedback'])
        C1copy['feedback'] = None
        print("\tMultiplying feedback values by " + str(fb_fac))
    else:
        fb_fac = None

    with open(old,'r') as fin:
        with open(new,'w') as fout:
        
            for line in fin:   
                
                spl = line.split("=",1)

                if np.size(spl) == 2:
                    for key in C1copy:
                        if key.strip() == spl[0].strip():
                            val = str(C1copy[key]).strip()
                            C1copy[key]=None
                            print("\tChanging " + spl[0].strip() + " from " + spl[1].strip() + " to " + val.strip())
                            #spl[1] = val.rjust(len(spl[1])-1)
                            spl[1] = "  " + val
                            line = spl[0] + "=" + spl[1] + "\n"
                    
                    if (fb_fac is not None) and ('feedback' in spl[0]):
                        val = fb_fac*float(spl[1].strip())
                        spl[1] = "  " + str(val)
                        line = spl[0] + "=" + spl[1] + "\n"
                        
                if line.strip() != '/':
                    fout.write(line)
          
            if append:
                for key in C1copy:
                    val = C1copy[key]
                    if val is not None:
                        line = "\t"+str(key).strip()+"  =  "+str(val).strip()+"\n"
                        print("\tAppending " + line.strip())
                        fout.write('\n')
                        fout.write(line)
                fout.write('\n')
                    
            fout.write(' /\n')
            
    return
