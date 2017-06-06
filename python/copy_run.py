import os
from my_shutil import cp

def copy_run(src,dst):

    if not os.path.isdir(dst):
        os.mkdir(dst)
                
    cp(src+'/adapted0.smb',dst+'/adapted0.smb')
    cp(src+'/batch_slurm',dst+'/batch_slurm')
    cp(src+'/batch_torque',dst+'/batch_torque')
    cp(src+'/C1input',dst+'/C1input')
    cp(src+'/coil.dat',dst+'/coil.dat')
    cp(src+'/current.dat',dst+'/current.dat')
    cp(src+'/diiid0.020.smb',dst+'/diiid0.020.smb')
    cp(src+'/diiid0.02.smd',dst+'/diiid0.02.smd')
    cp(src+'/diiid0.02.sms',dst+'/diiid0.02.sms')
    cp(src+'/diiid0.02.txt',dst+'/diiid0.02.txt')
    cp(src+'/geqdsk',dst+'/geqdsk')
    cp(src+'/profile_ne',dst+'/profile_ne')
    cp(src+'/profile_te',dst+'/profile_te')
    cp(src+'/profile_omega',dst+'/profile_omega')
    cp(src+'/profile_vphi',dst+'/profile_vphi')
    cp(src+'/rmp_coil.dat',dst+'/rmp_coil.dat')
    cp(src+'/rmp_current.dat',dst+'/rmp_current.dat')
    cp(src+'/sizefieldParam',dst+'/sizefieldParam')
    
    return
