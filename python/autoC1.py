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
from subprocess import call, check_output
from time import sleep
import re
import matplotlib.pyplot as plt
from matplotlib import gridspec

import my_shutil as mysh
from extend_profile import extend_profile
from load_equil import load_equil
from move_iter import move_iter
from mod_C1input import mod_C1input
from extract_profiles import extract_profiles

import C1py

def autoC1(task='all',machine='DIII-D',C1inputs=None,
           interactive=True, OMFIT=False, calcs=[(0,0,0)]):
    
    if task == 'all':
        task = 'setup'

    if OMFIT:
        interactive = False

    template = os.environ.get('AUTOC1_HOME')+'/templates/'+ machine + '/'
    
    if machine is 'DIII-D':
        rot = 'eb1'
    elif machine is 'NSTX-U':
        rot = 'eb1'
    elif machine is 'AUG':
        rot = 'eb1'
    else:
        rot = 'eb1'

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

        if not OMFIT:
            mysh.cp(r'g*.*','geqdsk')
            extract_profiles(machine=machine)

        if machine in ['DIII-D','NSTX-U']:

            fc = open('current.dat','w')
            mysh.cp(r'a*.*','a0.0')
            call(['a2cc', 'a0.0'], stdout=fc)
            fc.close()
            os.remove('a0.0')
            
        if interactive:
            next = '-'
                
            while next not in ['Y','N']:
                   
                next = raw_input('>>> Would you like to extend profile_ne and profile_te? (Y/N) ')
            
                if next == 'Y':
                    print  "Trying: extend_profile('profile_ne',minval=1e-2,psimax=1.1,psimin=0.95,center=0.98,width=0.01,smooth=None)"
                    loop_extprof('profile_ne',minval=1e-2,psimax=1.1,psimin=0.95,
                                 center=0.98,width=0.01,smooth=None)
                    os.rename('profile_ne.extpy','profile_ne')                
                    
                    print  "Trying: extend_profile('profile_te',minval=1e-4,psimax=1.1,psimin=0.95,center=0.98,width=0.01,smooth=None)"
                    loop_extprof('profile_te',minval=1e-4,psimax=1.1,psimin=0.95,
                                 center=0.98,width=0.01,smooth=None)                
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
        mod_C1input(C1inputs)
        call(submit_batch)
        print
        
        if machine in ['AUG']:
            while not os.path.exists('time_000.h5'):
                sleep(10)
            call("\idl -e '@get_aug_currents'",shell=True)
        
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
        mod_C1input(C1inputs)
        
        if interactive:
            while True:
                min_iter = raw_input('>>> Please enter minimum iteration number: ')
    
                try:
                    min_iter = int(min_iter)
                    if min_iter < 1:
                        print '*** min_iter must be greater than or equal to 1 ***'                    
                    else:
                        break
                except ValueError:
                    print '*** min_iter must be an integer ***'
        else:
            min_iter = 1
        
        iter = 0
        for iter in range(1,min_iter):
            
            call(submit_batch)
            print
            while not os.path.exists('time_000.h5'):
                sleep(10)
            print  '>>> iter '+str(iter)+' time_000.h5 created'
            print check_output('grep "Final error in GS solution" C1stdout',shell=True)
            
            os.mkdir('iter_'+str(iter))
            move_iter('iter_'+str(iter)+'/')
            
        next = 'Y'
        iter += 1
        
        while next != 'N':
        
            call(submit_batch)
            print
            while not os.path.exists('time_000.h5'):
                sleep(10)
            print
            print  '>>> iter '+str(iter)+' time_000.h5 created'
            print check_output('grep "Final error in GS solution" C1stdout',shell=True)
            os.mkdir('iter_'+str(iter))
            move_iter('iter_'+str(iter)+'/')
        
            if interactive:
                
                print '>>> Check the equilibrium match for iter_'+str(iter)
            
                next = '-'
                
                while next not in ['Y','N']:
                    
                    next = raw_input('>>> Would you like to do another iteration? (Y/N) ')
                    
                    if next == 'Y':
                        iter += 1
                    elif next == 'N':
                        break
                    else:
                        print '*** Improper response ***'
            else:
                next = 'N'
            
        else: 
            print '>>> Continuing to mesh adaptation'
            print '>>> Check the equilibrium match for iter_'+str(iter)
            
        
        print
        print '>>> Stopped equilibrium iteration after ',iter,' iterations'
        
        os.chdir('..')        
        
        if interactive:
            
            next = '-'
                
            while next not in ['Y','N']:
                
                next = raw_input('>>> Would you like to continue onto mesh adaptation? (Y/N) ')
    
                if next == 'Y':
                    mysh.cp('uni_equil/iter_'+str(iter)+'/current.dat','uni_equil/current.dat.good')
                    continue
                elif next == 'N':
                    return
                else:
                    print '*** Improper response ***'
        
        else:
            
            f = plt.figure(figsize=(16,5))
            gs= gridspec.GridSpec(1,4,width_ratios=[4,5,5,5])
            fs = 0.5
            ax = plt.subplot(gs[0])
            C1py.plot_shape(folder=['uni_efit/','uni_equil/iter_1/'],
                            rrange=[1.0,2.5],zrange=[-1.25,1.25],
                            fs=fs,ax=ax,title='Shape')
            leg = ax.legend(fontsize=24*fs,frameon=True,loc=[0.6,0.85])
            leg.get_frame().set_facecolor('white')
            plts = [('ne',r'$n_e$',plt.subplot(gs[1])),
                    ('te',r'$T_e$',plt.subplot(gs[2])),
                    ('ti',r'$T_i$',plt.subplot(gs[3]))]
            for field,title,ax in plts:
                C1py.plot_field(field,filename='uni_equil/iter_1/C1.h5',
                                slice=-1,rrange=[1.0,2.5],zrange=[-1.25,1.25],
                                lcfs=True,range=[-1,1],fs=fs,ax=ax,
                                title=title,palette='coolwarm')
            f.tight_layout()
            f.savefig('equil_check.pdf')
            
            mysh.cp('uni_equil/iter_'+str(iter)+'/current.dat','uni_equil/current.dat.good')
                    
    
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
        mod_C1input(C1inputs)
        
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
    
    
    if interactive:
        calcs = None
    else:
        ncalc = 0
    
    opts = {'0':'exit',
            '1':'equilibrium',
            '2':'stability',
            '3':'response',
            '4':'examine'}

    while True:

        if task == 'calculation':
            
            if interactive:
                
                print '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%'
                print '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%'
                print
                print '>>> What kind of calculation would you like to perform?'
                print '>>> 1)  Equilibrium'
                print '>>> 2)  Linear stability'
                print '>>> 3)  Linear 3D response'
                print '>>> 4)  Examine results with IDL'
                print
                
                option = '-'
                
                while option not in opts:
                    option = raw_input('>>> Please enter the desired option (1-4, 0 to exit): ')
                    if option not in opts:
                        print '*** Improper response ***'
                        
                print
                
                task = opts[option]
                
            else:
                    
                if ncalc == len(calcs):
                    task = exit
                else:
                    
                    option, ntor, nflu = calcs[ncalc]
                    task = opts[option]
                    print task + ' calculation'
                    if ntor is not None:
                        print '   n='+ntor 
                    if nflu is not None:
                        print '   '+nflu+'-fluid'
                    print
        
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
            mod_C1input(C1inputs)
        
            call(submit_batch)
            print
            
            print  '>>> Job m3dc1_equil submitted'
            
            if interactive:
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
        
            if interactive:
                while True:
                    ntor = raw_input('>>> Please enter the desired ntor: ')
    
                    try:
                        int(ntor)
                        break
                    except ValueError:
                        print '*** ntor must be an integer ***'
    
    
                nflu = ''
                while nflu not in ['1','2']:
                    
                    nflu = raw_input('>>> How many fluids? (1 or 2) ')
                        
                    if nflu not in ['1','2']:
                        print '*** Improper response ***'                
                
                print
            
            print 'Calculating stability for '+nflu+'F and ntor = ' + ntor
    
            ndir = 'n='+ntor+'/'
            
            if not os.path.isdir(ndir):
                os.mkdir(ndir)
            os.chdir(ndir)
            
            stab = rot+'_'+nflu+'f_stab/'
            if not os.path.isdir(stab):
                sh.copytree(template+'n=/'+stab,stab)
        
            load_equil('../rw1_adapt/',stab)
            mysh.cp('../rw1_adapt/adapted0.smb', stab+'adapted0.smb')
            os.chdir(stab)
            mod_C1input(C1inputs)
            for line in fileinput.input('C1input',inplace=1):
                print re.sub(r'ntor = ','ntor = '+ntor,line.rstrip('\n'))
        
            call(submit_batch)
            print
            print  '>>> Job m3dc1_stab submitted'
            
            if interactive:
                print  '>>> You can do other calculations in the meantime'
                raw_input('>>> Press <ENTER> twice to start another calculation')
                raw_input('>>> Press <ENTER> again to proceed')
            
            os.chdir('../..')
            print
            print
            
        elif task == 'response':
            
            print '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%'
            print 'Calculate 3D plasma response'
            print '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%'
            print
                
            if interactive:  
                while True:
                    ntor = raw_input('>>> Please enter the desired ntor: ')
    
                    try:
                        int(ntor)
                        break
                    except ValueError:
                        print '*** ntor must be an integer ***'
                    
                nflu = ''
                while nflu not in ['1','2']:
                    
                    nflu = raw_input('>>> How many fluids? (1 or 2) ')
                        
                    if nflu not in ['1','2']:
                        print '*** Improper response ***'
                             
                
                print
                
            print 'Calculating '+nflu+'F response for ntor = ' + ntor
    
            ndir = 'n='+ntor+'/'
            
            if not os.path.isdir(ndir):
                os.mkdir(ndir)
            os.chdir(ndir)
            
            up = rot+'_'+nflu+'f_iu/'
            low = rot+'_'+nflu+'f_il/'
            
            if not os.path.isdir(up):
                sh.copytree(template+'n=/'+up,up)
            load_equil('../rw1_adapt/',up)
            mysh.cp('../rw1_adapt/adapted0.smb', up+'adapted0.smb')
            os.chdir(up)
            mod_C1input(C1inputs)
            for line in fileinput.input('C1input',inplace=1):
                print re.sub(r'ntor = ','ntor = '+ntor,line.rstrip('\n'))
            call(submit_batch)
            
            os.chdir('..')
            
            if not os.path.isdir(low):
                sh.copytree(template+'n=/'+low,low)
            load_equil('../rw1_adapt/',low)
            mysh.cp('../rw1_adapt/adapted0.smb', low+'adapted0.smb')
            os.chdir(low)
            mod_C1input(C1inputs)
            for line in fileinput.input('C1input',inplace=1):
                print re.sub(r'ntor = ','ntor = '+ntor,line.rstrip('\n'))
            call(submit_batch)
                
            print
            print  '>>> Jobs m3dc1_iu and m3dc1_il submitted'
            if interactive:            
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
            
            if interactive:
                next = '-'
                
                while next not in ['Y','N']:
                    
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
                        
                        while okay not in ['Y','N']:
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
            
            else:
                print ">>> In non-interactive mode"
                print ">>> Please launch IDL separately"
            
        task = 'calculation'
        if not interactive:
            ncalc +=1 
    
    return    

# Loop over extend_profile until it is acceptable to the user
def loop_extprof(filename,minval=0.,psimax=1.05,psimin=0.95,center=0.98,
                 width=0.01,smooth=None):

    good = 'N'

    plt.ion()
    while good is not 'Y': 

        extend_profile(filename,minval=minval,psimax=psimax,psimin=psimin,
                       center=center,width=width,smooth=smooth)
        
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
            
            try:
                center = float(raw_input('>>> New center: (<Enter> for same value '+str(center)+') '))
            except ValueError:
                print 'center = '+str(center)+' unchanged'
            
            try:
                width = float(raw_input('>>> New width: (<Enter> for same value '+str(width)+') '))
            except ValueError:
                print 'width = '+str(width)+' unchanged'
            
            try:
                sm_str = raw_input('>>> New smooth: (<Enter> for same value '+str(smooth)+') ')
                if sm_str is 'None':
                    smooth = None
                else:
                    smooth = float(sm_str)
            except ValueError:
                print 'smooth = '+str(smooth)+' unchanged'
            
    
    plt.ioff()
    plt.close('all')
    
    return
        
        
        
        
        
        
