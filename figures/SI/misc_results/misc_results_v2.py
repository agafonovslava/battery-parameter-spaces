#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 20 07:29:14 2018

@author: peter

"""

import numpy as np
import matplotlib.pyplot as plt
import glob
import pickle
from scipy.stats import rankdata, kendalltau, pearsonr
from cycler import cycler

plt.close('all')

MAX_WIDTH = 183 / 25.4 # mm -> inches
figsize=(MAX_WIDTH, MAX_WIDTH)

# IMPORT RESULTS
# Get pickle files of bounds
file_list = sorted(glob.glob('./bounds/[0-9]_bounds.pkl'))
data = []
for file in file_list:
    with open(file, 'rb') as infile:
        param_space, ub, lb, mean = pickle.load(infile)
        data.append(mean)

# Get folder path containing predictions
pred_data = []
file_list = sorted(glob.glob('./pred/[0-9].csv'))
for k,file_path in enumerate(file_list):
    pred_data.append(np.genfromtxt(file_path, delimiter=','))

## Find number of batches and protocols
n_batches  = len(data)
n_protocols = len(param_space)

## find mean change
change = np.zeros((n_protocols, n_batches-1))
for k, batch in enumerate(data[:-1]):
    change[:,k] = data[k+1] - data[k]

mean_change = np.mean(np.abs(change),axis=0)

## find mean change as a percent
per_change = np.zeros((n_protocols, n_batches-1))
for k, batch in enumerate(data[:-1]):
    per_change[:,k] = 100*(data[k+1] - data[k])/data[k+1]

mean_per_change = np.mean(np.abs(per_change),axis=0)

## find mean change for top K protocols
top_K_protocols_list = [5,10,50,224]
mean_change_topk = np.zeros((len(top_K_protocols_list),n_batches-1))
mean_per_change_topk = np.zeros((len(top_K_protocols_list),n_batches-1))

for k, n in enumerate(top_K_protocols_list):
    top_protocol_idx = np.argsort(-mean)[0:n]
    mean_change_topk[k,:] = np.mean(np.abs(change[top_protocol_idx]),axis=0)
    mean_per_change_topk[k,:] = np.mean(np.abs(per_change[top_protocol_idx]),axis=0)

## find change in rankings per kendall tau
tau = np.zeros((len(top_K_protocols_list),n_batches-2))
for k1, n in enumerate(top_K_protocols_list):
    top_protocol_idx = np.argsort(-mean)[0:n]
    for k2 in [1,2,3]: # don't start with 0 - all are tied
        ranks1 = len(param_space) - rankdata(data[k2])[top_protocol_idx]
        ranks2 = len(param_space) - rankdata(data[k2+1])[top_protocol_idx]
        #print(k1,k2,ranks1,ranks2)
        tau[k1,k2-1] = kendalltau(ranks1,ranks2)[0]

## plot
batches = np.arange(n_batches-1)+1
plt.subplots(3,3,figsize=figsize)

ax0 = plt.subplot2grid((3, 3), (0, 0))  
ax1 = plt.subplot2grid((3, 3), (0, 1))  
ax2 = plt.subplot2grid((3, 3), (0, 2))
ax3 = plt.subplot2grid((3, 3), (1, 0))
ax4 = plt.subplot2grid((3, 3), (1, 1))
ax5 = plt.subplot2grid((3, 3), (1, 2))
ax6 = plt.subplot2grid((3, 3), (2, 0), colspan=3)

ax0.set_title('a', loc='left', weight='bold', fontsize=8)
ax1.set_title('b', loc='left', weight='bold', fontsize=8)
ax2.set_title('c', loc='left', weight='bold', fontsize=8)
ax3.set_title('d', loc='left', weight='bold', fontsize=8)
ax4.set_title('e', loc='left', weight='bold', fontsize=8)
ax5.set_title('f', loc='left', weight='bold', fontsize=8)
ax6.set_title('g', loc='left', weight='bold', fontsize=8)

## plot
batches = np.arange(n_batches-1)+1

cm = plt.get_cmap('winter')

legend = ['$K$ = ' + str(k) for k in top_K_protocols_list]

color_cycler = (cycler(color=[cm(1.*i/len(top_K_protocols_list)) for i in range(len(top_K_protocols_list))]))

ax0.set_prop_cycle(color_cycler)
for i in range(len(top_K_protocols_list)-1):
    ax0.plot(batches,mean_per_change_topk[i])
ax0.plot(batches,mean_per_change_topk[i+1],'k')
ax0.set_xlabel('Batch index\n(change from round $i-1$ to $i$)')
ax0.set_ylabel('Mean change in estimated\ncycle life for top $K$ protocols (%)')
ax0.set_ylim((0,14))
ax0.set_xticks(np.arange(1, 5, step=1))
ax0.legend(legend,frameon=False)

# Abs. change
ax1.set_prop_cycle(color_cycler)
for i in range(len(top_K_protocols_list)-1):
    ax1.plot(batches,mean_change_topk[i])
ax1.plot(batches,mean_change_topk[i+1],'k')
ax1.set_xlabel('Batch index\n(change from round $i-1$ to $i$)')
ax1.set_ylabel('Mean change in estimated\ncycle life for top $K$ protocols (cycles)')
ax1.set_ylim((0,140))
ax1.set_xticks(np.arange(1, 5, step=1))
ax1.legend(legend,frameon=False)

# Tau
ax2.set_prop_cycle(color_cycler)
for i in range(len(top_K_protocols_list)-1):
    ax2.plot(batches[1:],tau[i])
ax2.plot(batches[1:],tau[i+1],'k')
ax2.set_xlabel('Batch index\n(change from round $i-1$ to $i$)')
ax2.set_ylabel('Change in Kendall rank correlation\ncoefficient for top $K$ protocols')
ax2.set_ylim((0,1))
ax2.set_xticks(np.arange(2, 5, step=1))
ax2.legend(legend,frameon=False)

## Histogram
with plt.style.context(('classic')):
    ax3.hist(data[-1], bins=12, range=(600,1200),color=[0.1,0.4,0.8])
ax3.set_xlabel('CLO-estimated cycle life\nafter round 4, $\mathit{μ_{4,i}}$ (cycles)')
ax3.set_ylabel('Number of protocols')
ax3.set_xlim([600,1200])

## Sum of squares correlation

# add cc4 to protocols
protocols = []
for k, prot in enumerate(param_space):
    cc4 = 0.2/(1/6 - (0.2/prot[0] + 0.2/prot[1] + 0.2/prot[2])) # analytical expression for cc4
    protocols.append([prot[0], prot[1], prot[2],cc4])
    
protocols = np.asarray(protocols) # cast to numpy array

## MODELS
values = np.sum(protocols**2,axis=1)

xlabel_mod = r'$\mathdefault{sum(}I\mathdefault{^2)=\Sigma}_{j=1}^{4}\mathdefault{CC}_j^2$ (C rate$^2$)'
rho = pearsonr(values,mean)[0]
leglabel = r'$\rho$ = {:.2f}'.format(rho)

ax4.plot(values, mean, 'o', label=leglabel, color=[0.1,0.4,0.8])
ax4.set_xlabel(xlabel_mod)
ax4.set_ylabel('CLO-estimated cycle life\nafter round 4, $\mathit{μ_{4,i}}$ (cycles)')
ax4.legend(loc='best', markerscale=0, frameon=False)

## Bounds vs mean
ye = [(mean-lb)/(5*0.5**5),(ub-mean)/(5*0.5**5)]
rho = pearsonr(mean,ye[0])[0]
leglabel = r'$\rho$ = {:.2f}'.format(rho)

ax5.plot(mean,ye[0],'o',color=[0.1,0.4,0.8],label=leglabel)
ax5.set_xlabel('CLO-estimated cycle life\nafter round 4, $\mathit{μ_{4,i}}$ (cycles)')
ax5.set_ylabel('Standard deviation of cycle life\nafter round 4, $\mathit{σ_{4,i}}$ (cycles)')
ax5.set_xlim([590,1210])
ax5.legend(loc='best',markerscale=0,frameon=False)

## Bounds, colored by repetitions
num_batches=5 # 4 batches, plus one

isTested = np.zeros(len(protocols))

mean  = mean[top_protocol_idx]
ye[0] = ye[0][top_protocol_idx]
ye[1] = ye[1][top_protocol_idx]

for k, prot in enumerate(param_space[top_protocol_idx]):
    for batch in pred_data:
        for row in batch:
            if (prot==row[0:3]).all():
                isTested[k] += 1

colors = [cm(1.*i/num_batches) for i in range(num_batches)]
colors[0] = (0,0,0,1)

leg = [str(i)+" repetitions" for i in np.arange(num_batches)]
leg[1] = "1 repetition"

for k in np.arange(num_batches):
    idx = np.where(isTested==k)
    ye2 = [ye[0][idx],ye[1][idx]]
    ax6.errorbar(np.arange(224)[idx]+1, mean[idx], yerr=ye2, fmt='o',
                 color=colors[k], capsize=2, label=leg[k])

ax6.set_xlim((0,225))
ax6.set_xlabel('Protocol rank after round 4')
ax6.set_ylabel('Mean ± standard deviation of cycle life\nafter round 4, $\mathit{\mu_{4,i} \pm \sigma_{4,i}}$ (cycles)')
ax6.legend(frameon=False)

plt.tight_layout()
plt.savefig('misc_results_v2.png', dpi=300)
plt.savefig('misc_results_v2.eps', format='eps')