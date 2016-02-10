from my_shutil import cp
def load_equil(src,dst):
    cp(src+'/geqdsk',dst+'/geqdsk')
    cp(src+'/profile_ne',dst+'/profile_ne')
    cp(src+'/profile_te',dst+'/profile_te')
    cp(src+'/profile_omega',dst+'/profile_omega')
    cp(src+'/current.dat',dst+'/current.dat')
    return
