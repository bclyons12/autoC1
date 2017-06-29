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
import copy
from subprocess import call, check_output, Popen
from time import sleep
import matplotlib.pyplot as plt

import my_shutil as mysh
from extend_profile import extend_profile
from load_equil import load_equil
from move_iter import move_iter
from mod_C1input import mod_C1input
from extract_profiles import extract_profiles
from sedpy import sedpy

def autoC1(task='all', machine='DIII-D', calcs=[(0,0,0)],
           interactive=True, OMFIT=False,
           setup_folder='efit', uni_equil_folder='uni_equil',
           adapt_folder='rw1_adapt', adapted_mesh=None, parallel_adapt=False,
           C1input_mod=None, C1input_base='C1input_base',rot='eb',
           saturn_partition='batch',nersc_repo='atom'):
    
    if task == 'all':
        task = 'setup'

    if OMFIT:
        interactive = False

    # Until we figure out how to combine meshes
    if parallel_adapt:
        raise ValueError('Parallel mesh adaption not yet functional')

    template = os.environ.get('AUTOC1_HOME')+'/templates/'+ machine + '/'
    

    C1arch = os.environ.get('AUTOC1_ARCH')


    # Setup C1input
    
    if not os.path.exists(C1input_base):
        mysh.cp(template+'/C1input_base',C1input_base)

    iread_eqdsks = {'DIII-D':'3',
                    'NSTX-U':'3',
                    'AUG':'1',
                    'KSTAR':'3'}
    
    uni_smb  = {'DIII-D':'diiid0.02.smb',
                'NSTX-U':'nstxu0.02.smb',
                'AUG':   'aug0.02.smb',
                'KSTAR': 'kstar-0.02-2.20-3.60-7K.smb'}
    uni0_smb = {'DIII-D':'diiid0.020.smb',
               'NSTX-U':'nstxu0.020.smb',
               'AUG':   'aug0.020.smb',
               'KSTAR': 'kstar-0.02-2.20-3.60-7K0.smb'}
    uni_txt = {'DIII-D':'diiid0.02.txt',
               'NSTX-U':'nstxu0.02.txt',
               'AUG':   'aug0.02.txt',
               'KSTAR': 'kstar-0.02-2.20-3.60.txt'}
    
    coils = {'DIII-D':['iu','il'],
             'NSTX-U':['iu','il'],
             'AUG':   ['iu','il'],
             'KSTAR': ['tfec','mfec','bfec']}
    
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
                                'mesh_filename':"'%s'"%uni_smb[machine],
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

    # Setup batch file and slurm command
    bash_commands = {'efit':'part_mesh.sh '+uni_smb[machine]+' $SLURM_NTASKS',
                     'uni_equil':'part_mesh.sh '+uni_smb[machine]+' $SLURM_NTASKS',
                     'adapt':'echo $SLURM_JOB_ID > job_id.txt',
                     'equilibrium':'part_mesh.sh adapted.smb $SLURM_NTASKS',
                     'stability':'part_mesh.sh adapted.smb $SLURM_NTASKS',
                     'response':'part_mesh.sh adapted.smb $SLURM_NTASKS'}
    if parallel_adapt:
        bash_commands['adapt'] += '\n'+'part_mesh.sh '+uni_smb[machine]+' $SLURM_NTASKS'

    exec_commands = {'sunfire':'mpiexec --bind-to none -np ',
                     'iris': 'mpiexec --bind-to none -np ',
                     'saturn': 'mpiexec --bind-to none -np ',
                     'cori-haswell':'srun -n ',
                     'cori-knl':'srun -n ',
                     'edison':'srun -n '}

    standard_ea = '$SLURM_NTASKS m3dc1_2d_complex -pc_factor_mat_solver_package mumps >& C1stdout'
    adapt_ea = {False:'1 m3dc1_2d >& C1stdout',
                True: '$SLURM_NTASKS m3dc1_2d >& C1stdout'}
    exec_args = {'efit':standard_ea,
                 'uni_equil':standard_ea,
                 'adapt':adapt_ea[parallel_adapt],
                 'equilibrium':standard_ea,
                 'stability':standard_ea,
                 'response':standard_ea}

    Psmall = {'sunfire':'kruskal,dawson,mque,ellis',
              'iris':'short',
              'saturn':saturn_partition,
              'cori-haswell':'debug,regular',
              'cori-knl':'debug,regular',
              'edison':'debug'}

    Plarge = {'sunfire':'mque',
              'iris':'medium',
              'saturn':saturn_partition,
              'cori-haswell':'regular',
              'cori-knl':'regular',
              'edison':'regular'}

    Padapt = copy.deepcopy(Plarge)
    if not parallel_adapt:
        Padapt['cori-haswell']='shared'

    slurm_options = {'sunfire':{'efit':['--partition='+Psmall['sunfire'],
                                        '--nodes=1',
                                        '--ntasks=16',
                                        '--time=0:10:00',
                                        '--mem=32000',
                                        '--job-name=m3dc1_efit'],
                                'uni_equil':['--partition='+Psmall['sunfire'],
                                             '--nodes=1',
                                             '--ntasks=16',
                                             '--time=0:10:00',
                                             '--mem=32000',
                                             '--job-name=m3dc1_eq'],
                                'adapt':{False:['--partition='+Padapt['sunfire'],
                                                '--nodes=1',
                                                '--ntasks=1',
                                                '--time=4:00:00',
                                                '--mem=60000',
                                                '--job-name=m3dc1_adapt'],
                                         True:['--partition='+Plarge['sunfire'],
                                               '--nodes=1',
                                               '--ntasks=32',
                                               '--time=0:30:00',
                                               '--mem=256000',
                                               '--job-name=m3dc1_adapt']},
                                'equilibrium':['--partition='+Plarge['sunfire'],
                                               '--nodes=1',
                                               '--ntasks=16',
                                               '--time=1:00:00',
                                               '--mem=120000',
                                               '--job-name=m3dc1_equil'],
                                'stability':['--partition='+Plarge['sunfire'],
                                             '--nodes=1',
                                             '--ntasks=32',
                                             '--time=12:00:00',
                                             '--mem=256000',
                                             '--job-name=m3dc1_stab'],
                                'response':['--partition='+Plarge['sunfire'],
                                            '--nodes=1',
                                            '--ntasks=32',
                                            '--time=4:00:00',
                                            '--mem=256000']},
                     'iris': {'efit':['--partition='+Psmall['iris'],
                                      '--nodes=1',
                                      '--ntasks=16',
                                      '--time=0:10:00',
                                      '--mem=32000',
                                      '--job-name=m3dc1_efit'],
                              'uni_equil':['--partition='+Psmall['iris'],
                                           '--nodes=1',
                                           '--ntasks=16',
                                           '--time=0:10:00',
                                           '--mem=32000',
                                           '--job-name=m3dc1_eq'],
                              'adapt':{False:['--partition='+Padapt['iris'],
                                              '--nodes=1',
                                              '--ntasks=1',
                                              '--time=4:00:00',
                                              '--mem=60000',
                                              '--job-name=m3dc1_adapt'],
                                       True:['--partition='+Plarge['iris'],
                                             '--nodes=1',
                                             '--ntasks=16',
                                             '--time=4:00:00',
                                             '--mem=120000',
                                             '--job-name=m3dc1_adapt']},
                              'equilibrium':['--partition='+Plarge['iris'],
                                             '--nodes=1',
                                             '--ntasks=16',
                                             '--time=2:00:00',
                                             '--mem=120000',
                                             '--job-name=m3dc1_equil'],
                              'stability':['--partition='+Plarge['iris'],
                                           '--nodes=1',
                                           '--ntasks=16',
                                           '--time=24:00:00',
                                           '--mem=120000',
                                           '--job-name=m3dc1_stab'],
                              'response':['--partition='+Plarge['iris'],
                                          '--nodes=1',
                                          '--ntasks=16',
                                          '--time=8:00:00',
                                          '--mem=120000']},
                     'saturn': {'efit':['--partition='+Psmall['saturn'],
                                        '--ntasks=16',
                                        '--time=0:10:00',
                                        '--mem=120000',
                                        '--job-name=m3dc1_efit'],
                                'uni_equil':['--partition='+Psmall['saturn'],
                                             '--ntasks=16',
                                             '--time=0:30:00',
                                             '--mem=120000',
                                             '--job-name=m3dc1_eq'],
                                'adapt':{False:['--partition='+Padapt['saturn'],
                                                '--ntasks=1',
                                                '--time=4:00:00',
                                                '--mem=120000',
                                                '--job-name=m3dc1_adapt'],
                                         True:['--partition='+Plarge['saturn'],
                                               '--ntasks=32',
                                               '--time=0:30:00',
                                               '--mem=240000',
                                               '--job-name=m3dc1_adapt']},
                                'equilibrium':['--partition='+Plarge['saturn'],
                                               '--ntasks=16',
                                               '--time=2:00:00',
                                               '--mem=120000',
                                               '--job-name=m3dc1_equil'],
                                'stability':['--partition='+Plarge['saturn'],
                                             '--ntasks=32',
                                             '--time=12:00:00',
                                             '--mem=240000',
                                             '--job-name=m3dc1_stab'],
                                'response':['--partition='+Plarge['saturn'],
                                            '--ntasks=32',
                                            '--time=2:00:00',
                                            '--mem=240000']},
                     'cori-haswell':{'efit':['--partition='+Psmall['cori-haswell'],
                                             '--qos=normal',
                                             '--constraint=haswell',
                                             '--account='+nersc_repo,
                                             '--nodes=1',
                                             '--ntasks=32',
                                             '--time=0:10:00',
                                             '--job-name=m3dc1_efit'],
                                     'uni_equil':['--partition='+Psmall['cori-haswell'],
                                                  '--qos=normal',
                                                  '--constraint=haswell',
                                                  '--account='+nersc_repo,
                                                  '--nodes=1',
                                                  '--ntasks=32',
                                                  '--time=0:10:00',
                                                  '--job-name=m3dc1_eq'],
                                     'adapt':{False:['--partition='+Padapt['cori-haswell'],
                                                     '--qos=normal',
                                                     '--constraint=haswell',
                                                     '--account='+nersc_repo,
                                                     '--ntasks=1',
                                                     '--time=4:00:00',
                                                     '--mem=60000',
                                                     '--job-name=m3dc1_adapt'],
                                              True:['--partition='+Plarge['cori-haswell'],
                                                    '--qos=normal',
                                                    '--constraint=haswell',
                                                    '--account='+nersc_repo,
                                                    '--nodes=2',
                                                    '--ntasks=64',
                                                    '--time=0:30:00',
                                                    '--job-name=m3dc1_adapt']},
                                     'equilibrium':['--partition='+Plarge['cori-haswell'],
                                                    '--qos=normal',
                                                    '--constraint=haswell',
                                                    '--account='+nersc_repo,
                                                    '--nodes=2',
                                                    '--ntasks=64',
                                                    '--time=0:05:00',
                                                    '--job-name=m3dc1_equil'],
                                     'stability':['--partition='+Plarge['cori-haswell'],
                                                  '--qos=normal',
                                                  '--constraint=haswell',
                                                  '--account='+nersc_repo,
                                                  '--nodes=2',
                                                  '--ntasks=64',
                                                  '--time=2:00:00',
                                                  '--job-name=m3dc1_stab'],
                                     'response':['--partition='+Plarge['cori-haswell'],
                                                 '--qos=normal',
                                                 '--constraint=haswell',
                                                 '--account='+nersc_repo,
                                                 '--nodes=2',
                                                 '--ntasks=64',
                                                 '--time=0:10:00']},
                     'cori-knl':{'efit':['--partition='+Psmall['cori-knl'],
                                         '--qos=normal',
                                         '--constraint=knl,quad,cache',
                                         '--account='+nersc_repo,
                                         '--nodes=1',
                                         '--ntasks=64',
                                         '--time=0:05:00',
                                         '--job-name=m3dc1_efit'],
                                 'uni_equil':['--partition='+Psmall['cori-knl'],
                                              '--qos=normal',
                                              '--constraint=knl,quad,cache',
                                              '--account='+nersc_repo,
                                              '--nodes=1',
                                              '--ntasks=64',
                                              '--time=0:05:00',
                                              '--job-name=m3dc1_eq'],
                                 'adapt':{False:['--partition='+Padapt['cori-knl'],
                                                 '--qos=normal',
                                                 '--constraint=knl,quad,cache',
                                                 '--account='+nersc_repo,
                                                 '--ntasks=1',
                                                 '--time=1:00:00',
                                                 '--mem=60000',
                                                 '--job-name=m3dc1_adapt'],
                                          True:['--partition='+Plarge['cori-knl'],
                                                '--qos=normal',
                                                '--constraint=knl,quad,cache',
                                                '--account='+nersc_repo,
                                                '--nodes=1',
                                                '--ntasks=64',
                                                '--time=0:30:00',
                                                '--job-name=m3dc1_adapt']},
                                 'equilibrium':['--partition='+Plarge['cori-knl'],
                                                '--qos=normal',
                                                '--constraint=knl,quad,cache',
                                                '--account='+nersc_repo,
                                                '--nodes=1',
                                                '--ntasks=64',
                                                '--time=0:05:00',
                                                '--job-name=m3dc1_equil'],
                                 'stability':['--partition='+Plarge['cori-knl'],
                                              '--qos=normal',
                                              '--constraint=knl,quad,cache',
                                              '--account='+nersc_repo,
                                              '--nodes=1',
                                              '--ntasks=64',
                                              '--time=2:00:00',
                                              '--job-name=m3dc1_stab'],
                                 'response':['--partition='+Plarge['cori-knl'],
                                             '--qos=normal',
                                             '--constraint=knl,quad,cache',
                                             '--account='+nersc_repo,
                                             '--nodes=1',
                                             '--ntasks=64',
                                             '--time=0:10:00']},
                     'edison':{'efit':['--partition='+Psmall['edison'],
                                       '--account='+nersc_repo,
                                       '--nodes=1',
                                       '--ntasks=24',
                                       '--time=0:10:00',
                                       '--job-name=m3dc1_efit'],
                               'uni_equil':['--partition='+Psmall['edison'],
                                            '--account='+nersc_repo,
                                            '--nodes=1',
                                            '--ntasks=24',
                                            '--time=0:10:00',
                                            '--job-name=m3dc1_eq'],
                               'adapt':{False:['--partition='+Padapt['edison'],
                                               '--qos=normal',
                                               '--account='+nersc_repo,
                                               '--ntasks=1',
                                               '--time=1:00:00',
                                               '--mem=60000',
                                               '--job-name=m3dc1_adapt'],
                                        True:['--partition='+Plarge['edison'],
                                              '--qos=normal',
                                              '--account='+nersc_repo,
                                              '--nodes=2',
                                              '--ntasks=48',
                                              '--time=0:30:00',
                                              '--job-name=m3dc1_adapt']},
                               'equilibrium':['--partition='+Plarge['edison'],
                                              '--qos=normal',
                                              '--account='+nersc_repo,
                                              '--nodes=2',
                                              '--ntasks=48',
                                              '--time=0:10:00',
                                              '--job-name=m3dc1_equil'],
                               'stability':['--partition='+Plarge['edison'],
                                            '--qos=normal',
                                            '--account='+nersc_repo,
                                            '--nodes=2',
                                            '--ntasks=48',
                                            '--time=2:00:00',
                                            '--job-name=m3dc1_stab'],
                               'response':['--partition='+Plarge['edison'],
                                           '--qos=normal',
                                           '--account='+nersc_repo,
                                           '--nodes=2',
                                           '--ntasks=48',
                                           '--time=1:00:00']}
    }
    
    
    base_files = ['batch_slurm','coil.dat','sizefieldParam',
                  uni0_smb[machine],uni_txt[machine]]
        
    if task == 'setup':

        print '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%'
        print 'Setting up equilibrium files in efit/'
        print '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%'
        print
        
        os.chdir(setup_folder)

        if not OMFIT:
            mysh.cp(r'g*.*','geqdsk')
            extract_profiles(machine=machine)

        pppl_bin  = '/p/tsc/nferraro/src/svn_local/trunk/unstructured/_sunfire.openmpi-1.8.4/'
        ga_bin    = '/fusion/projects/codes/m3dc1/m3dc1-iris-1.8-devel/bin/'
        nersc_bin = '/global/project/projectdirs/mp288/C1/m3dc1-cori-1.8-devel/bin/'
        a2cc_bin = {'sunfire':pppl_bin,
                    'iris':ga_bin,
                    'saturn':ga_bin,
                    'cori-haswell':nersc_bin,
                    'cori-knl':nersc_bin,
                    'edison':nersc_bin}

        a2cc = {'DIII-D':'a2cc',
                'NSTX-U':'a2cc',
                'KSTAR':a2cc_bin[C1arch]+'a2cc'}
        if machine in ['DIII-D','NSTX-U','KSTAR']:

            fc = open('current.dat','w')
            mysh.cp(r'a*.*','a0.0')
            call([a2cc[machine], 'a0.0'], stdout=fc)
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
    
        # create folder
        efit_folder = 'uni_efit'
        if os.path.isdir(efit_folder):
            print 'Warning:  '+efit_folder+' exists and may be overwritten'
        os.mkdir(efit_folder)
        
        # load necessary files
        for f in base_files:
            mysh.cp(template+f,efit_folder+'/'+f)
        load_equil(setup_folder,efit_folder)
        mysh.cp(C1input_base,efit_folder+'/C1input')
        os.chdir(efit_folder)
        
        # modify C1input file
        C1input_efit = dict(C1input_options[task])
        if C1input_mod is not None:
            C1input_efit.update(C1input_mod)
        mod_C1input(C1input_efit)
        
        # modify and sumbit batch_slurm
        sedpy('BASH_COMMAND',bash_commands[task],'batch_slurm')
        sedpy('EXEC_COMMAND',exec_commands[C1arch]+exec_args[task],'batch_slurm')
        submit_batch = ['sbatch']+slurm_options[C1arch][task]+['batch_slurm']
        write_command(submit_batch)
        call(submit_batch)
        print
        
        if machine in ['AUG']:
            while not os.path.exists('time_000.h5'):
                sleep(10)
            mysh.cp(template+'get_aug_currents.pro','./get_aug_currents.pro')
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
        os.mkdir(uni_equil_folder)
        
        for f in base_files:
            mysh.cp(template+f,uni_equil_folder+'/'+f)
        load_equil(setup_folder,uni_equil_folder)
        mysh.cp(C1input_base,uni_equil_folder+'/C1input')
        os.chdir(uni_equil_folder)
        
        
        C1input_uni_equil = dict(C1input_options[task])
        if C1input_mod is not None:
            C1input_uni_equil.update(C1input_mod)
        mod_C1input(C1input_uni_equil)
        
        sedpy('BASH_COMMAND',bash_commands[task],'batch_slurm')
        sedpy('EXEC_COMMAND',exec_commands[C1arch]+exec_args[task],'batch_slurm')
        submit_batch = ['sbatch']+slurm_options[C1arch][task]+['batch_slurm']
        
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
        os.mkdir(adapt_folder)
        
        
        for f in base_files:
            mysh.cp(template+f,adapt_folder+'/'+f)
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
        
            sedpy('BASH_COMMAND',bash_commands[task],'batch_slurm')
            sedpy('EXEC_COMMAND',exec_commands[C1arch]+exec_args[task],'batch_slurm')
            submit_batch = ['sbatch']+slurm_options[C1arch][task][parallel_adapt]+['batch_slurm']
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
            os.mkdir(equil_folder)
            
            for f in base_files:
                mysh.cp(template+f,equil_folder+'/'+f)
            load_equil(adapt_folder,equil_folder)
            mysh.cp(C1input_base,equil_folder+'/C1input')
            mysh.cp(adapt_folder+'/adapted0.smb', 
                    equil_folder+'/adapted0.smb')
            os.chdir(equil_folder)
            
            C1input_equil = dict(C1input_options[task])
            if C1input_mod is not None:
                C1input_equil.update(C1input_mod)
            mod_C1input(C1input_equil)
        
            sedpy('BASH_COMMAND',bash_commands[task],'batch_slurm')
            sedpy('EXEC_COMMAND',exec_commands[C1arch]+exec_args[task],'batch_slurm')
            submit_batch = ['sbatch']+slurm_options[C1arch][task]+['batch_slurm']
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
            
            stab_folder = def_folder(rot,nflu+'f_stab')
            os.mkdir(stab_folder)
            
            for f in base_files:
                mysh.cp(template+f,stab_folder+'/'+f)
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
            
            sedpy('BASH_COMMAND',bash_commands[task],'batch_slurm')
            sedpy('EXEC_COMMAND',exec_commands[C1arch]+exec_args[task],'batch_slurm')
            submit_batch = ['sbatch']+slurm_options[C1arch][task]+['batch_slurm']
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
            
            for coil in coils[machine]:
                
                resp_folder = def_folder(rot,nflu+'f_'+coil)
                os.mkdir(resp_folder)
                
                for f in base_files:
                    mysh.cp(template+f,resp_folder+'/'+f)
                mysh.cp(template+'rmp_coil_'+coil+'.dat',
                        resp_folder+'/rmp_coil.dat')
                mysh.cp(template+'rmp_current_'+coil+'.dat',
                        resp_folder+'/rmp_current.dat')
                load_equil('../'+adapt_folder,resp_folder)
                mysh.cp('../'+C1input_base,resp_folder+'/C1input')
                mysh.cp('../'+adapt_folder+'/adapted0.smb', 
                        resp_folder+'/adapted0.smb')
                os.chdir(resp_folder)
                
                mod_C1input(C1input_resp)
                
                job_name = 'm3dc1_'+coil
                sedpy('BASH_COMMAND',bash_commands[task],'batch_slurm')
                sedpy('EXEC_COMMAND',exec_commands[C1arch]+exec_args[task],'batch_slurm')
                submit_batch = ['sbatch']+slurm_options[C1arch][task]
                submit_batch += ['--job-name='+job_name]+['batch_slurm']
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
        h.write('\n')
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
    
