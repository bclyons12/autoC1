# autoC1
Scripts and templates for automatically running M3D-C1


-------------------------------------------------------------------------------
autoC1 script
-------------------------------------------------------------------------------

The fundamental python function is autoC1() which has the following call pattern

autoC1(task='all',machine='DIII-D')

*********
task
*********

Tasks proceed in the following order. 
You can skip to a step by setting this keyword to the desired value.
Folder in which a given step occurs is given with parentheses.

'all'         - Starts from the beginning with 'setup' [DEFAULT]
'setup'       - Preprocess the g-, p-, and a-files into readable formats ('efit/')
	        Allows user to extend the profiles beyond the separatrix.
'efit'        - Perform an igs=0 run to get the EFIT equilibrium ('uni_efit/')
'uni_equil'   - Perform equilibrium calcalutions on a uniform mesh ('uni_equil/')
	        User can iterate on current.dat.out in this step to improve 
	            the equilibrium match to the EFIT.
	        Can launch IDL within this step to check the equilibrium match.
'adapt'       - Adapt the mesh to the equilibrium ('rw1_adapt/')
'calculation' - Perform linear calculations with adapted mesh.
	      	User will select from four options.
		1) Calculate equilibrium ('rw1_equil/')
		2) Linear stability analysis ('n=<ntor>/eb1_1f_stab/')
		   User selects desired toroidal mode number <ntor>
		   Currently uses ExB rotation and single-fluid only
		3) Time-independent, linear response ('n=<ntor>/eb1_1f_<coil>/')
		   User selects desired toroidal mode number <ntor>
		   <coil> values are defined by the machine
		   Currently uses ExB rotation and single-fluid only
		One can also open IDL to examine the results within this step.

*********
machine
*********

Name of device to be modeled, so appropriate templates can be found.
Currently 'DIII-D' [DEFAULT] and 'NSTX-U' are supported.


-------------------------------------------------------------------------------
Download and setup
-------------------------------------------------------------------------------

1) Create a base directory to store the autoC1 scripts and templates.

2) Set the AUTOC1_HOME environmental variable to this base directory.

3) cd to this directory

4) Download autoC1 from github
   A) On portalr6, run 'git clone git@github.com:bclyons12/autoC1.git'
   B) On saturn,   run 'git clone https://github.com/bclyons12/autoC1.git'

5) Add $AUTOC1_HOME/python/ to your PYTHONPATH environmental variable

6) Import the appropriate python module on your system.  I use:
   A) On portalr6, 'module load anaconda'
   B) On saturn,   'module load python'


-------------------------------------------------------------------------------
Running autoC1
-------------------------------------------------------------------------------

1) Create a new working directory for the current runs

2) Create a folder called 'efit/' within this working directory

3) Populate 'efit/' with the g*.*, p*.*, and a*.* file for this shot & time

4) From the base working directory, run 'python'

5) Within python, import the autoC1 function from the autoC1 module.
   For example:  from autoC1 import autoC1

6) Run the autoC1 function (see above for keyword details)

7) The script should walk you through it's steps in a self-explanatory way.
   It will ask for user input when required, as long as prompt you to check certain things
   about the runs along the way.