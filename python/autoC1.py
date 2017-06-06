# -*- coding: utf-8 -*-
"""
autoC1

Script to run M3D-C1 automatically

Author:       Brendan Carrick Lyons
Date created: Thu Feb  4 16:43:40 2016
Date edited:  
"""

import os
import sys
import shutil as sh
from subprocess import call, check_output, Popen
from time import sleep
import matplotlib.pyplot as plt

import my_shutil as mysh
from extend_profile import extend_profile
from load_equil import load_equil
from move_iter import move_iter
from mod_C1input import mod_C1input
from extract_profiles import extract_profiles

def autoC1(task='all', machine='DIII-D', calcs=[(0,0,0)],
           interactive=True, OMFIT=False,
           setup_folder='efit', uni_equil_folder='uni_equil',
           adapt_folder='rw1_adapt', adapted_mesh=None,
           C1input_mod=None, C1input_base='C1input_base'):
    
    if task == 'all':
        task = 'setup'

    if OMFIT:
        interactive = False

    template = os.environ.get('AUTOC1_HOME')+'/templates/'+ machine + '/'
    
    if machine is 'DIII-D':
        rot = 'eb'
    elif machine is 'NSTX-U':
        rot = 'eb'
    elif machine is 'AUG':
        rot = 'eb'
    else:
        rot = 'eb'

    C1arch = os.environ.get('AUTOC1_ARCH')

    if C1arch == 'sunfire':

        part_small = 'kruskal,dawson,mque,ellis'
        part_large = 'mque'
        batch_file = 'batch_slurm'

        batch_options = {'efit':['--partition='+part_small,
                                 '--nodes=1',
                                 '--ntasks=16',
                                 '--time=0:10:00',
                                 '--mem=32000',
                                 '--job-name=m3dc1_efit'],
                         'uni_equil':['--partition='+part_small,
                                      '--nodes=1',
                                      '--ntasks=16',
                                      '--time=0:10:00',
                                      '--mem=32000',
                                      '--job-name=m3dc1_eq'],
                         'adapt':['--partition='+part_large,
                                  '--nodes=1',
                                  '--ntasks=1',
                                  '--time=4:00:00',
                                  '--mem=60000',
                                  '--job-name=m3dc1_adapt'],
                         'equilibrium':['--partition='+part_large,
                                        '--nodes=1',
                                        '--ntasks=16',
                                        '--time=1:00:00',
                                        '--mem=120000',
                                        '--job-name=m3dc1_equil'],
                         'stability':['--partition='+part_large,
                                      '--nodes=1',
                                      '--ntasks=32',
                                      '--time=12:00:00',
                                      '--mem=256000',
                                      '--job-name=m3dc1_stab'],
                         'response':['--partition='+part_large,
                                     '--nodes=1',
                                     '--ntasks=32',
                                     '--time=4:00:00',
                                     '--mem=256000']}
        
        
    elif C1arch == 'saturn':
        
        part_small = 'short'
        part_large = 'medium'
        batch_file = 'batch_slurm'
        
        batch_options = {'efit':['--partition='+part_small,
                                 '--nodes=1',
                                 '--ntasks=16',
                                 '--time=0:10:00',
                                 '--mem=32000',
                                 '--job-name=m3dc1_efit'],
                         'uni_equil':['--partition='+part_small,
                                      '--nodes=1',
                                      '--ntasks=16',
                                      '--time=0:10:00',
                                      '--mem=32000',
                                      '--job-name=m3dc1_eq'],
                         'adapt':['--partition='+part_large,
                                  '--nodes=1',
                                  '--ntasks=8',
                                  '--time=4:00:00',
                                  '--mem=60000',
                                  '--job-name=m3dc1_adapt'],
                         'equilibrium':['--partition='+part_large,
                                        '--nodes=1',
                                        '--ntasks=16',
                                        '--time=2:00:00',
                                        '--mem=128000',
                                        '--job-name=m3dc1_equil'],
                         'stability':['--partition='+part_large,
                                      '--nodes=1',
                                      '--ntasks=16',
                                      '--time=24:00:00',
                                      '--mem=128000',
                                      '--job-name=m3dc1_stab'],
                         'response':['--partition='+part_large,
                                     '--nodes=1',
                                     '--ntasks=16',
                                     '--time=8:00:00',
                                     '--mem=128000']}
        
    elif C1arch == 'edison':
        
        part_small = 'debug'
        part_adapt = 'shared'
        part_large = 'regular, --qos=normal'
        batch_file = 'batch_edison'
        
        batch_options = {'efit':['--partition='+part_small,
                                 '--constraint=haswell',
                                 '--nodes=1',
                                 '--ntasks=32',
                                 '--time=0:10:00',
                                 '--mem=120000',
                                 '--job-name=m3dc1_efit'],
                         'uni_equil':['--partition='+part_small,
                                      '--constraint=haswell',
                                      '--nodes=1',
                                      '--ntasks=32',
                                      '--time=0:10:00',
                                      '--mem=120000',
                                      '--job-name=m3dc1_eq'],
                         'adapt':['--partition='+part_adapt,
                                  '--constraint=haswell',
                                  '--ntasks=1',
                                  '--time=4:00:00',
                                  '--mem=60000',
                                  '--job-name=m3dc1_adapt'],
                         'equilibrium':['--partition='+part_small,
                                        '--constraint=haswell',
                                        '--nodes=4',
                                        '--ntasks=128',
                                        '--time=0:30:00',
                                        '--mem=240000',
                                        '--job-name=m3dc1_equil'],
                         'stability':['--partition='+part_large,
                                      '--constraint=haswell',
                                      '--nodes=4',
                                      '--ntasks=128',
                                      '--time=4:00:00',
                                      '--mem=240000',
                                      '--job-name=m3dc1_stab'],
                         'response':['--partition='+part_small,
                                     '--constraint=haswell',
                                     '--nodes=4',
                                     '--ntasks=128',
                                     '--time=0:30:00',
                                     '--mem=240000']}
        
    else:
        print 'Error: autoC1 does not support AUTOC1_ARCH = '+C1arch
        return 

        
    # Setup C1input
    
    if not os.path.exists(C1input_base):
        mysh.cp(template+'/C1input_base',C1input_base)

    iread_eqdsks = {'DIII-D':'3',
                   'NSTX-U':'3',
                   'AUG':'1'}
    mesh_filenames   = {'DIII-D':"'diiid0.02.smb'",
                        'NSTX-U':"'nstxu0.02.smb'",
                        'AUG':"'aug0.02.smb'"}

    C1input_options = {'efit':{'ntimemax':'0',
                               'ntimepr':'1',
                               'iread_eqdsk':'1',
                               'irmp':'0',
                               'extsubtract':'0',
                               'max_ke':'0',
                               'itime_independent':'1',
                               'idevice':'4',
                               'eps':'0',
                               'db_fac':'0.0',
                               'mesh_filename':"'part.smb'",
                               'icsubtract':'0',
                               'igs':'0',
                               'ntor':'0'},
                       'uni_equil':{'ntimemax':'0',
                                    'ntimepr':'1',
                                    'iread_eqdsk':iread_eqdsks[machine],
                                    'irmp':'0',
                                    'extsubtract':'0',
                                    'max_ke':'0',
                                    'itime_independent':'1',
                                    'idevice':'-1',
                                    'eps':'0',
                                    'db_fac':'0.0',
                                    'mesh_filename':"'part.smb'",
                                    'icsubtract':'1',
                                    'ntor':'0'},
                       'adapt':{'ntimemax':'0',
                                'ntimepr':'1',
                                'iread_eqdsk':iread_eqdsks[machine],
                                'irmp':'0',
                                'extsubtract':'0',
                                'iadapt':'1',
                                'adapt_smooth':'0.02',
                                'max_ke':'0',
                                'itime_independent':'1',
                                'idevice':'-1',
                                'eps':'0',
                                'db_fac':'0.0',
                                'mesh_filename':mesh_filenames[machine],
                                'icsubtract':'1',
                                'ntor':'0'},
                       'equilibrium':{'ntimemax':'0',
                                      'ntimepr':'1',
                                      'iread_eqdsk':iread_eqdsks[machine],
                                      'irmp':'0',
                                      'extsubtract':'0',
                                      'max_ke':'0',
                                      'itime_independent':'1',
                                      'idevice':'-1',
                                      'eps':'0',
                                      'db_fac':'0.0',
                                      'mesh_filename':"'part.smb'",
                                      'icsubtract':'1',
                                      'ntor':'0'},
                       'stability':{'iread_eqdsk':iread_eqdsks[machine],
                                    'irmp':'0',
                                    'extsubtract':'0',
                                    'max_ke':'1',
                                    'itime_independent':'0',
                                    'idevice':'-1',
                                    'eps':'1e-8',
                                    'mesh_filename':"'part.smb'",
                                    'icsubtract':'1'},
                       'response':{'ntimemax':'1',
                                   'ntimepr':'1',
                                   'iread_eqdsk':iread_eqdsks[machine],
                                   'irmp':'1',
                                   'extsubtract':'1',
                                   'max_ke':'0',
                                   'itime_independent':'1',
                                   'idevice':'-1',
                                   'eps':'0',
                                   'mesh_filename':"'part.smb'",
                                   'icsubtract':'1'}}
        
        
    if task == 'setup':

        print '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%'
        print 'Setting up equilibrium files in efit/'
        print '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%'
        print
        
        os.chdir(setup_folder)

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
    
        efit_folder = 'uni_efit'
        if os.path.isdir(efit_folder):
            print 'Warning:  '+efit_folder+' exists and may be overwritten'
        sh.copytree(template+'uni_efit/',efit_folder)
        
        load_equil(setup_folder,efit_folder)
        mysh.cp(C1input_base,efit_folder+'/C1input')
        os.chdir(efit_folder)
        
        C1input_efit = dict(C1input_options[task])
        if C1input_mod is not None:
            C1input_efit.update(C1input_mod)
        mod_C1input(C1input_efit)
        
        submit_batch = ['sbatch']+batch_options[task]+[batch_file]
        write_command(submit_batch)
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
    
        uni_equil_folder = 'uni_equil'
        
        if os.path.isdir(uni_equil_folder):
            print 'Warning:  '+uni_equil_folder+' exists and may be overwritten'
        sh.copytree(template+'uni_equil/',uni_equil_folder)
        
        load_equil(setup_folder,uni_equil_folder)
        mysh.cp(C1input_base,uni_equil_folder+'/C1input')
        os.chdir(uni_equil_folder)
        
        
        C1input_uni_equil = dict(C1input_options[task])
        if C1input_mod is not None:
            C1input_uni_equil.update(C1input_mod)
        mod_C1input(C1input_uni_equil)
        
        submit_batch = ['sbatch']+batch_options[task]+[batch_file]
        
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
            
            write_command(submit_batch)
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
        
            write_command(submit_batch)
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
                    mysh.cp(uni_equil_folder+'/iter_'+str(iter)+'/current.dat',
                            uni_equil_folder+'/current.dat.good')
                    continue
                elif next == 'N':
                    return
                else:
                    print '*** Improper response ***'
        
        else:
            
            plot_script = os.environ.get('AUTOC1_HOME')+'/python/plot_equil_check.py'
            Popen([sys.executable,'-u',plot_script])
            mysh.cp(uni_equil_folder+'/iter_'+str(iter)+'/current.dat',
                    uni_equil_folder+'/current.dat.good')
                    
    
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
    
        adapt_folder = def_folder('rw','adapt')
        
        sh.copytree(template+'rw1_adapt/',adapt_folder)
        
        load_equil(setup_folder,adapt_folder)
        mysh.cp(uni_equil_folder+'/current.dat.good',
                adapt_folder+'/current.dat')

        if adapted_mesh is None:
            # Perform mesh adaptation
            mysh.cp(C1input_base,adapt_folder+'/C1input')
            os.chdir(adapt_folder)
        
            C1input_adapt = dict(C1input_options[task])
            if C1input_mod is not None:
                C1input_adapt.update(C1input_mod)
            mod_C1input(C1input_adapt)
        
            submit_batch = ['sbatch']+batch_options[task]+[batch_file]
            write_command(submit_batch)
            call(submit_batch)
            print
            
            print  '>>> Wait for adapted0.smb to be created'
            while not os.path.exists('adapted0.smb'):
                sleep(10)
        
            print  '>>> Mesh adaptation complete'

            with open('job_id.txt','r') as f:
                jobid = f.read().rstrip('\n')
            print  '>>> Killing m3dc1_adapt job #'+jobid
            call(['scancel',jobid])
    
            os.chdir('..')

        else:
            mysh.cp(adapted_mesh,adapt_folder+'/adapted0.smb')
            print
            print  '>>> Using provided adapted mesh'

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
            
            equil_folder = def_folder('rw','equil')
            sh.copytree(template+'rw1_equil/',equil_folder)
        
            load_equil(adapt_folder,equil_folder)
            mysh.cp(C1input_base,equil_folder+'/C1input')
            mysh.cp(adapt_folder+'/adapted0.smb', 
                    equil_folder+'/adapted0.smb')
            os.chdir(equil_folder)
            
            C1input_equil = dict(C1input_options[task])
            if C1input_mod is not None:
                C1input_equil.update(C1input_mod)
            mod_C1input(C1input_equil)
        
            submit_batch = ['sbatch']+batch_options[task]+[batch_file]
            write_command(submit_batch)
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
            
            base_folder = rot+'1_stab'
            stab_folder = def_folder(rot,nflu+'f_stab')
            sh.copytree(template+'n=/'+base_folder,stab_folder)
        
            load_equil('../'+adapt_folder,stab_folder)
            mysh.cp('../'+C1input_base,stab_folder+'/C1input')
            mysh.cp('../'+adapt_folder+'/adapted0.smb',
                    stab_folder+'/adapted0.smb')
            os.chdir(stab_folder)
            
            C1input_stab = dict(C1input_options[task])
            C1input_stab.update({'ntor':ntor})
            if nflu == '1':
                C1input_stab.update({'db_fac':'0.0'})
            elif nflu == '2':
                C1input_stab.update({'db_fac':'1.0'})
            if C1input_mod is not None:
                C1input_stab.update(C1input_mod)
            mod_C1input(C1input_stab)
            
            submit_batch = ['sbatch']+batch_options[task]+[batch_file]
            write_command(submit_batch)
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
            
            C1input_resp = dict(C1input_options[task])
            C1input_resp.update({'ntor':ntor})
            if nflu == '1':
                C1input_resp.update({'db_fac':'0.0'})
            elif nflu == '2':
                C1input_resp.update({'db_fac':'1.0'})
            if C1input_mod is not None:
                C1input_resp.update(C1input_mod)
            
            for coil in ['iu','il']:
                
                base_folder = rot+'1_'+coil
                resp_folder = def_folder(rot,nflu+'f_'+coil)
                sh.copytree(template+'n=/'+base_folder,resp_folder)
                
                load_equil('../'+adapt_folder,resp_folder)
                mysh.cp('../'+C1input_base,resp_folder+'/C1input')
                mysh.cp('../'+adapt_folder+'/adapted0.smb', 
                        resp_folder+'/adapted0.smb')
                os.chdir(resp_folder)
                
                mod_C1input(C1input_resp)
                
                job_name = 'm3dc1_'+coil
                submit_batch = ['sbatch']+batch_options[task]
                submit_batch += ['--job-name='+job_name]+[batch_file]
                write_command(submit_batch)
                call(submit_batch)
            
                os.chdir('..')
                print  '>>> Job ' + job_name + ' submitted'
            
            print
            
            if interactive:            
                print  '>>> You can do other calculations in the meantime'
                raw_input('>>> Press <ENTER> twice to start another calculation')
                raw_input('>>> Press <ENTER> again to proceed')
                
            os.chdir('..')
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
        
        
def write_command(submit_batch):
    
    with open("submit_command","w") as h:
        h.write(' '.join(submit_batch))
    
    return

def def_folder(pre,post):
    
    i = 1
    
    while True:
        
        folder = pre+str(i)+'_'+post

        if os.path.isdir(folder):
            i += 1
        else:
            break
        
    return folder
    
