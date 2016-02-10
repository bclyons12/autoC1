from my_shutil import mv
def move_iter(dst):
    mv('*.h5',dst)
    mv('C1ke',dst)
    mv('C1stdout',dst)
    mv('current.dat',dst)
    mv('current.dat.out','current.dat')
    return
