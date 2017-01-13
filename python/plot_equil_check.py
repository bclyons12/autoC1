import matplotlib.pyplot as plt
from matplotlib import gridspec
import C1py

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
plt.show()
            