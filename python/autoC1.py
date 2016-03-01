# -*- coding: utf-8 -*-
"""
autoC1

Script to run M3D-C1 automatically

Author:       Brendan Carrick Lyons
Date created: Thu Feb  4 16:43:40 2016
Date edited:  
"""

import os
import shutil as sh
import fileinput
from subprocess import call
from time import sleep
import re

import my_shutil as mysh
from extend_profile import extend_profile
from load_equil import load_equil
from move_iter import move_iter

def autoC1(task='setup',machine='DIII-D'):
    
    if task == 'all':
        task = 'setup'


    template = os.environ.get('AUTOC1_HOME')+'/templates/'+ machine + '/'

    C1arch = os.environ.get('M3DC1_ARCH')

    if C1arch == 'sunfire.r6':
        submit_batch = ['sbatch','batch_slurm']
    elif C1arch == 'saturn':
        submit_batch = ['qsub','batch_torque']
    else:
        print 'Error: autoC1 does not support M3DC1_ARCH = '+C1arch
        return 

    if task == 'setup':

        print '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%'
        print 'Setting up equilibrium files in efit/'
        print '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%'
        print
        
        os.chdir('efit/')
        mysh.cp(r'g*.*','geqdsk')
        

        mysh.cp(r'p*.*','p0.0')
        
        # extract profiles using Nate's utility        
        call(['extract_profiles.sh', 'p0.0'])
        
        # extact the Carbon toroidal rotation from the p-file
        with open('p0.0','r') as fin:
            iprint = False
            for line in fin:
                if not iprint:
                    if 'psinorm omeg' in line:
                        iprint = True
                        fout = open('profile_omega.Ctor','w')
                else:
                    if 'psinorm'  not in line:
                        fout.write(line)
                    else:
                        iprint = False
                        fout.close()

        os.remove('p0.0')

        fc = open('current.dat','w')
        mysh.cp(r'a*.*','a0.0')
        call(['a2cc', 'a0.0'], stdout=fc)
        fc.close()
        os.remove('a0.0')

        next = '-'
            
        while next not in 'YN':
               
            next = raw_input('>>> Would you like to extend profile_ne and profile_te? (Y/N) ')
        
            if next == 'Y':
                print  "Trying: extend_profile('profile_ne',minval=1e-2,psimax=1.1,psimin=0.95)"
                loop_extprof('profile_ne',minval=1e-2,psimax=1.1,psimin=0.95)
                
                print  "Trying: extend_profile('profile_ne',minval=1e-4,psimax=1.1,psimin=0.95)"
                loop_extprof('profile_te',minval=1e-4,psimax=1.1,psimin=0.95)
                
                os.rename('profile_ne.extpy','profile_ne')
                os.rename('profile_te.extpy','profile_te')
                
                print
                print  'Using extended profiles'
                print
            elif next == 'N':
                print  'Using default profiles'
            else:
                print '*** Improper response ***'
        
        os.chdir('..')
    
        task = 'efit'
        
        print
        print
    
    else:
        print 'Skipping setup of equilibrium files'
        print
        
    
    if task == 'efit':
    
        print '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%'
        print 'Calculating EFIT equilibrium in uni_efit/'
        print '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%'
        print
    
        if not os.path.isdir('uni_efit/'):
            sh.copytree(template+'uni_efit/','uni_efit')
        
        load_equil('efit/','uni_efit/')
        os.chdir('uni_efit/')
        call(submit_batch)
        print
        
        print  '>>> Please wait for job m3dc1_efit to finish'
        raw_input('>>> Press <ENTER> twice when finished')
        raw_input('>>> Press <ENTER> again to proceed')
        
        os.chdir('..')
    
        task = 'uni_equil'
        
        print
        print
    else:
        print 'Skipping calculation of EFIT equilibrium'
        print
        
    
    if task == 'uni_equil':
    
        print '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%'
        print 'Calculating equilibrium with M3D-C1 GS solver in uni_equil/'
        print '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%'
        print
    
        if not os.path.isdir('uni_equil/'):
            sh.copytree(template+'uni_equil/','uni_equil')
        
        load_equil('efit/','uni_equil/')
        os.chdir('uni_equil/')
        
        iter = 1
        next = 'Y'
        
        while next != 'N':
        
            call(submit_batch)
            print
            print  '>>> Please wait for job m3dc1_eq'+str(iter)+' to finish'
            raw_input('>>> Press <ENTER> twice when finished')
            raw_input('>>> Press <ENTER> again to proceed')
            print
        
            os.mkdir('iter_'+str(iter))
            move_iter('iter_'+str(iter)+'/')
        
            print '>>> Check the equilibrium match for iter_'+str(iter)
        
            next = '-'
            
            while next not in 'YN':
                
                next = raw_input('>>> Would you like to do another iteration? (Y/N) ')
                
                if next == 'Y':
                    iter+=1
                elif next == 'N':
                    break
                else:
                    print '*** Improper response ***'
        
        print
        print '>>> You stopped equilibrium iteration after ',iter,' iterations'
        
        next = '-'
        os.chdir('..')
            
        while next not in 'YN':
            
            next = raw_input('>>> Would you like to continue onto mesh adaptation? (Y/N) ')

            if next == 'Y':
                mysh.cp('uni_equil/iter_'+str(iter)+'/current.dat','uni_equil/current.dat.good')
                continue
            elif next == 'N':
                return
            else:
                print '*** Improper response ***'
                
    
        task = 'adapt'
        
        print
        print
        
    else:
        print 'Skipping calculation of equilibrium with M3D-C1 GS solver'
        print
    
    if task == 'adapt':
        
        print '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%'
        print 'Adapting mesh to equilibrium in rw1_adapt/'
        print '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%'
        print
    
        if not os.path.isdir('rw1_adapt/'):
            sh.copytree(template+'rw1_adapt/','rw1_adapt')
        
        load_equil('efit/','rw1_adapt/')
        mysh.cp('uni_equil/current.dat.good', 'rw1_adapt/current.dat')
        os.chdir('rw1_adapt/')
        
        
        call(submit_batch)
        print
        
        print  '>>> Wait for adapted0.smb to be created'
        while not os.path.exists('adapted0.smb'):
            sleep(10)
        
        print  '>>> Mesh adaptation complete'
    
        os.chdir('..')
    
        task = 'calculation'
        
        print
        print
    
    else:
        print 'Skipping mesh adaptation'
        print
    
    
    while True:
        
        if task == 'calculation':
            
            print '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%'
            print '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%'
            print
            print '>>> What kind of calculation would you like to perform?'
            print '>>> 1)  Equilibrium'
            print '>>> 2)  Linear stability'
            print '>>> 3)  Linear 3D response'
            print '>>> 4)  Examine results with IDL'
            print
            
            calcs = {'0':'exit',
                     '1':'equilibrium',
                     '2':'stability',
                     '3':'response',
                     '4':'examine'}
            
            option = '-'
            
            while option not in calcs:
                option = raw_input('>>> Please enter the desired option (1-4, 0 to exit): ')
                if option not in calcs:
                    print '*** Improper response ***'
                    
            print
            
            task = calcs[option]

        
        if task == 'exit':
            print 'Exiting'
            return
        elif task == 'equilibrium':
            
            print '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%'
            print 'Calculate equilibrium with adapted mesh'
            print '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%'
            print
            
            if not os.path.isdir('rw1_equil/'):
                sh.copytree(template+'rw1_equil/','rw1_equil')
        
            load_equil('rw1_adapt/','rw1_equil/')
            mysh.cp('rw1_adapt/adapted0.smb', 'rw1_equil/adapted0.smb')
            os.chdir('rw1_equil/')
        
            call(submit_batch)
            print
            
            print  '>>> Job m3dc1_equil submitted'
            print  '>>> You can do other calculations in the meantime'
            raw_input('>>> Press <ENTER> twice to start another calculation')
            raw_input('>>> Press <ENTER> again to proceed')
            
            os.chdir('..')
            print
            print
    
        elif task == 'stability':
            
            print '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%'
            print 'Calculate linear stability'
            print '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%'
            print
        
            print '>>> Default ntor = 2'
            
            next = '-'
        
            while next not in 'YN':
                
                next = raw_input('>>> Would you like a different ntor? (Y/N) ')
    
                if next == 'Y':
                    print
                    
                    while True:
                        ntor = raw_input('>>> Please enter the desired ntor: ')

                        try:
                            int(ntor)
                            break
                        except ValueError:
                            print '*** ntor must be an integer ***'
                
                elif next == 'N':
                    ntor = '2'
                else:
                    print '*** Improper response ***'
                    
            print
            print 'Calculating stability for ntor = ' + ntor
    
            ndir = 'n='+ntor+'/'
            
            if not os.path.isdir(ndir):
                os.mkdir(ndir)
            os.chdir(ndir)
        
            if not os.path.isdir('eb1_1f_stab/'):
                sh.copytree(template+'n=/eb1_1f_stab/','eb1_1f_stab')
        
            load_equil('../rw1_adapt/','eb1_1f_stab/')
            mysh.cp('../rw1_adapt/adapted0.smb', 'eb1_1f_stab/adapted0.smb')
            os.chdir('eb1_1f_stab/')
            for line in fileinput.input('C1input',inplace=1):
                print re.sub(r'ntor = ','ntor = '+ntor,line.rstrip('\n'))
        
            call(submit_batch)
            print
            print  '>>> Job m3dc1_stab submitted'
            print  '>>> You can do other calculations in the meantime'
            raw_input('>>> Press <ENTER> twice to start another calculation')
            raw_input('>>> Press <ENTER> again to proceed')
            
            os.chdir('../..')
            print
            print
            
        elif task == 'response':
            
            print '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%'
            print 'Calculate RMP response'
            print '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%'
            print
                
            print '>>> Default ntor = 2'
            next = '-'
        
            while next not in 'YN':
                
                next = raw_input('>>> Would you like a different ntor? (Y/N) ')
    
                if next == 'Y':
                    print
                    
                    while True:
                        ntor = raw_input('>>> Please enter the desired ntor: ')

                        try:
                            int(ntor)
                            break
                        except ValueError:
                            print '*** ntor must be an integer ***'
                
                elif next == 'N':
                    ntor = '2'
                else:
                    print '*** Improper response ***'
                    
            print
            print 'Calculating response for ntor = ' + ntor
    
            ndir = 'n='+ntor+'/'
            
            if not os.path.isdir(ndir):
                os.mkdir(ndir)
            os.chdir(ndir)
             
            if not os.path.isdir('eb1_1f_iu/'):
                sh.copytree(template+'n=/eb1_1f_iu/','eb1_1f_iu')
            load_equil('../rw1_adapt/','eb1_1f_iu/')
            mysh.cp('../rw1_adapt/adapted0.smb', 'eb1_1f_iu/adapted0.smb')
            os.chdir('eb1_1f_iu/')
            for line in fileinput.input('C1input',inplace=1):
                print re.sub(r'ntor = ','ntor = '+ntor,line.rstrip('\n'))
            call(submit_batch)
            
            os.chdir('..')
            
            if not os.path.isdir('eb1_1f_il/'):
                sh.copytree(template+'n=/eb1_1f_il/','eb1_1f_il')
            load_equil('../rw1_adapt/','eb1_1f_il/')
            mysh.cp('../rw1_adapt/adapted0.smb', 'eb1_1f_il/adapted0.smb')
            os.chdir('eb1_1f_il/')
            for line in fileinput.input('C1input',inplace=1):
                print re.sub(r'ntor = ','ntor = '+ntor,line.rstrip('\n'))
            call(submit_batch)
                
            print
            print  '>>> Jobs m3dc1_iu and m3dc1_il submitted'
            print  '>>> You can do other calculations in the meantime'
            raw_input('>>> Press <ENTER> twice to start another calculation')
            raw_input('>>> Press <ENTER> again to proceed')
            
            os.chdir('../..')
            print
            print
            
        elif task == 'examine':
            
            print '>>> Here are some good things to check:'
            print '>>> Is the adapted equilbrium a good shape match?'
            print ">>> Is 'jy' a good match to the EFIT?"
            print ">>> Does 'ne', 'te', 'ti', or 'p' go negative anywhere?"
            print
            
            next = '-'
            
            while next not in 'YN':
                
                next = raw_input('>>> Would you like to check the quality of the equilibrium? (Y/N) ')
                
                if next == 'Y':
                    print 'Launching IDL for checking quality of the equilibrium'
                    print 'Recommend the following commands, but modify as need be'
                    print 'e.g., rw1_equil/ can be replaced by a completed response or stability run in n=2/'
                    print "plot_shape,['uni_efit/','rw1_equil/']+'C1.h5',rrange=[1.0,2.5],zrange=[-1.25,1.25],thick=3,/iso"
                    print "plot_flux_average,'jy',-1,file=['uni_efit/','rw1_equil/']+'C1.h5',/mks,/norm,table=39,thick=3,bins=400,points=400"
                    print "plot_field,'ti',-1,R,Z,file='rw1_equil/C1.h5',/mks,points=400,cutz=0.,/ylog"
                    print
                    
                    call(['idl'])
                    
                    okay = '-'
                    
                    while okay not in 'YN':
                        okay = '>>> Is the equilibrium good enough to continue? (Y/N) '
                        
                        if okay == 'Y':
                            continue
                        elif okay == 'N':
                            return
                        else:
                            print '*** Improper response ***'
                
                elif next == 'N':
                    print  'Continuing, but equilibrium may have problems'
                else:
                    print '*** Improper response ***'
    
        task = 'calculation'
    
    return    

# Loop over extend_profile until it is acceptable to the user
def loop_extprof(filename,minval=0.,psimax=1.05,psimin=0.95):

    good = 'N'

    while good is not 'Y': 
               
        extend_profile(filename,minval=minval,psimax=psimax,psimin=psimin)
        
        good = raw_input('>>> Is this profile extension good enough? (Y/N) ')
        if good is not 'Y':
            try:
                minval = float(raw_input('>>> New minval: (<Enter> for same value '+str(minval)+') '))
            except ValueError:
                print 'minval = '+str(minval)+' unchanged'
            try:
                psimax = float(raw_input('>>> New psimax: (<Enter> for same value '+str(psimax)+') '))
            except ValueError:
                print 'psimax = '+str(psimax)+' unchanged'
            try:
                psimin = float(raw_input('>>> New psimin: (<Enter> for same value '+str(psimin)+') '))
            except ValueError:
                print 'psimin = '+str(psimin)+' unchanged'
    
    return
        
        
        
        
        
        
