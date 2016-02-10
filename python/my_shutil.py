import shutil
import glob

# Copy a file
def cp(src,dst):
    
    for file in glob.glob(src):
        shutil.copyfile(file, dst)
    return

# Move a file
def mv(src,dst):
    
    for file in glob.glob(src):
        shutil.move(file, dst)
    return
