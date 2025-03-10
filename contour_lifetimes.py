#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Creates map of 4-step policy space with associated lifetimes

Peter Attia
Last modified August 23, 2018
"""

from sim_with_seed import sim
import numpy as np
import matplotlib
import matplotlib.pyplot as plt

##############################################################################

# PARAMETERS TO CREATE POLICY SPACE
min_policy_bound, max_policy_bound = 3.6, 8
C3list = [3.6, 4.0, 4.4, 4.8, 5.2, 5.6]

C4_LIMITS = [0.1, 4.81] # Lower and upper limits specifying valid C4s
FILENAME = 'sim'

############################################################################## 
plt.close('all')
colormap = 'plasma_r'

# Import policies
policies = np.genfromtxt('policies_all.csv', delimiter=',')

one_step = 4.8
margin = 0.2 # plotting margin

## CALCULATE POLICY LIFETIMES
lifetime = np.zeros((len(policies),1))
for i in range(len(policies)):
    C1 = policies[i,0]
    C2 = policies[i,1]
    C3 = policies[i,2]
    C4 = 0.2/(1/6 - (0.2/C1 + 0.2/C2 + 0.2/C3))
    lifetime[i] = sim(C1,C2,C3,variance=False)

# Save csv with policies and lifetimes
f=open('policies_lifetimes_'+FILENAME+'.csv','a')
np.savetxt(f,np.c_[policies,lifetime],delimiter=',', fmt='%1.3f')
f.close()

## CREATE CONTOUR PLOT
# Calculate C4(CC1, CC2) values for contour lines
C1_grid = np.arange(min_policy_bound-margin,max_policy_bound + margin,0.01)
C2_grid = np.arange(min_policy_bound-margin,max_policy_bound + margin,0.01)
[X,Y] = np.meshgrid(C1_grid,C2_grid)

# Initialize plot
fig = plt.figure() # x = C1, y = C2, cuts = C3, contours = C4
plt.style.use('classic')
plt.rcParams.update({'font.size': 16})
plt.set_cmap(colormap)
manager = plt.get_current_fig_manager() # Make full screen
manager.window.showMaximized()
minn, maxx = min(lifetime), max(lifetime)

## MAKE PLOT
for k, c3 in enumerate(C3list):
    plt.subplot(2,3,k+1)
    plt.axis('square')
    
    C4 = 0.2/(1/6 - (0.2/X + 0.2/Y + 0.2/c3))
    C4[np.where(C4<C4_LIMITS[0])]  = float('NaN')
    C4[np.where(C4>C4_LIMITS[1])] = float('NaN')
    
    ## PLOT CONTOURS
    levels = np.arange(2.5,4.8,0.25)
    C = plt.contour(X,Y,C4,levels,zorder=1,colors='k')
    plt.clabel(C,fmt='%1.1f')
    
    ## PLOT POLICIES
    idx_subset = np.where(policies[:,2]==c3)
    policy_subset = policies[idx_subset,:][0]
    lifetime_subset = lifetime[idx_subset,:]
    plt.scatter(policy_subset[:,0],policy_subset[:,1],vmin=minn,vmax=maxx,
                c=lifetime_subset.ravel(),zorder=2,s=100)
    
    ## BASELINE
    if c3 == one_step:
        lifetime_onestep = sim(one_step, one_step, one_step,variance=False)
        plt.scatter(one_step,one_step,c=lifetime_onestep,vmin=minn,vmax=maxx,
                    marker='s',zorder=3,s=100)
    
    plt.title('C3=' + str(c3) + ': ' + str(len(policy_subset)) + ' policies',fontsize=16)
    plt.xlabel('C1')
    plt.ylabel('C2')
    plt.xlim((min_policy_bound-margin, max_policy_bound+margin))
    plt.ylim((min_policy_bound-margin, max_policy_bound+margin))

plt.tight_layout()

# Add colorbar
fig.subplots_adjust(right=0.8)
cbar_ax = fig.add_axes([0.85, 0.15, 0.05, 0.7])
norm = matplotlib.colors.Normalize(minn, maxx)
m = plt.cm.ScalarMappable(norm=norm, cmap=colormap)
m.set_array([])
cbar = fig.colorbar(m, cax=cbar_ax)
#plt.clim(min(lifetime),max(lifetime))
cbar.ax.set_title('Cycle life')

## SAVE FIGURE
plt.savefig('contour_lifetimes_' + FILENAME + '.png', bbox_inches='tight')