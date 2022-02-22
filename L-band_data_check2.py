#!/usr/bin/env python

import pandas as pd
from argparse import ArgumentParser
import matplotlib.pylab as plt
import socket

pd.options.mode.chained_assignment = None  # To remove pandas warnings: default='warn'

parser = ArgumentParser(description="Command line utility for checking the status of spliced L-band data.")
parser.add_argument('filename', type=str, help='Full path and filenmae to read')
parser.add_argument('-d', action='store_true', default=False, dest='show_details',help='Shows details on the bad ones.')
args = parser.parse_args()

filename = args.filename
show_details = args.show_details

#---------------------------
# Read in the full "A list" of stars
# This comes from the BL database.
#---------------------------
local_host = socket.gethostname()

if 'bl' in local_host:
    master_file = open('/home/obs/logs/target_list_5-50pc.lst')
else:
    master_file = open('/Users/jeenriquez/RESEARCH/SETI_BL/L_band/target_list_5-50pc.lst')

a_list_master = master_file.read().splitlines()

#---------------------------
# Find the good L-band data by:
# - Reading in the output from spider.
# -
#---------------------------
# Initial data frame set up

try:
    df = pd.read_csv(filename, sep=",|=", header=None,engine='python')
except:
    IOError('Error opening file: %s'%filename)

df2 = df.ix[:,1::2]
df2.columns = list(df.ix[0,0::2])

#Selection of high resolution data
df3 = df2[df2['file'].str.contains("gpuspec.0000.fil",na=False)]

#Selection of L band data (soft)
#df3 = df2[~((df2['Frequency of channel 1 (MHz)'] > 2251.4647) & (df2['Frequency of channel 1 (MHz)'] < 2251.4649))]
df3 = df3[df3['Frequency of channel 1 (MHz)'] < 2500]

#---------------------------
# Adding some extra columns for later look at the good set of data.

df3['bands_used'] = [df3['file'][ii].split('/')[-1].split('_')[1].replace('blc','') for ii in df3.index]
df3['mid_Freq'] = df3['Frequency of channel 1 (MHz)']-2.835503418452676e-06*df3['Number of channels']/2.

df3['Source Name'] = df3['Source Name'].str.upper()

#---------------------------
# Selecting only the targets in the A-list

#Selecting all the targets from the B list
df_targets_blist = df3[~df3['Source Name'].isin(a_list_master)]
df_targets_clist =  df3[df3['Source Name'].str.contains('_OFF',na=False)]
df_targets_blist = pd.concat([df_targets_blist,df_targets_clist])
else_list = df_targets_blist['Source Name'].unique()

#Selecting all the good targets from the A list
df_targets_alist = df3[~df3['Source Name'].isin(else_list)]

#---------------------------
#Showing some info

print '------      o      --------'
a_unique = df_targets_alist['Source Name'].unique()
print 'The total number of targets from the A-list that:\n'
print 'Observed and spliced is      : %i'%(len(a_unique))

#---------------------------
#Group the df_targets and look for the ones observed 3 times on the same day.
#Also,
#Group the df_targets and look for the ones observed 1 time or 2 times but need 3.
#---------------------------
#NOTE: here I'm not yet checking if the 3rd observation is complete just yet.

# G_dates = df_targets_alist['Gregorian date (YYYY/MM/DD)'].unique()
#
list_completed = []
list_incomplete_1 = []
list_incomplete_2 = []
list_incomplete_4 = []
#
# for G_date in G_dates:
#     df_single_date = df_targets_alist[df_targets_alist['Gregorian date (YYYY/MM/DD)'].str.contains(G_date,na=False)]
#     df_single_date_targets = df_single_date.groupby('Source Name').count()['file'] > 2
#     df_bool_list = df_single_date_targets.tolist()
#     list_completed += list(df_single_date_targets[df_bool_list].index.values)
#
#     #check if observed twice
#     df_single_date_targets = df_single_date.groupby('Source Name').count()['file'] == 2
#     df_bool_list = df_single_date_targets.tolist()
#     list_incomplete_2 += list(df_single_date_targets[df_bool_list].index.values)
#
#     #check if observed once
#     df_single_date_targets = df_single_date.groupby('Source Name').count()['file'] == 1
#     df_bool_list = df_single_date_targets.tolist()
#     list_incomplete_1 += list(df_single_date_targets[df_bool_list].index.values)
#
#     #check if observed more than 3 times
#     df_single_date_targets = df_single_date.groupby('Source Name').count()['file'] > 3
#     df_bool_list = df_single_date_targets.tolist()
#     list_incomplete_4 += list(df_single_date_targets[df_bool_list].index.values)

##Find the ones that have actually been observed 3 times, but have different observing day (obs are near midnight).
# extra_a_list = list(set(list_incomplete_1) & set(list_incomplete_2))
##and the oposite
# a_list_incomplete = list(set(list_incomplete_1) ^ set(list_incomplete_2))

## Selecting targets with incomplete observations
# list_incomplete_1x = list(set(list_incomplete_1) - set(extra_a_list))
# list_incomplete_2x = list(set(list_incomplete_2) - set(extra_a_list))


#---------------------------
# Grouping without date constrains.
df_targets = df_targets_alist.groupby('Source Name').count()['file'] >2
df_bool_list = df_targets.tolist()
list_completed += list(df_targets[df_bool_list].index.values)

df_targets = df_targets_alist.groupby('Source Name').count()['file'] ==2
df_bool_list = df_targets.tolist()
list_incomplete_2 += list(df_targets[df_bool_list].index.values)

df_targets = df_targets_alist.groupby('Source Name').count()['file'] ==1
df_bool_list = df_targets.tolist()
list_incomplete_1 += list(df_targets[df_bool_list].index.values)


df_list_incomplete_1 = df_targets_alist[df_targets_alist['Source Name'].isin(list_incomplete_1)]
alist_incomplete_1 = df_list_incomplete_1['Source Name'].unique()

df_list_incomplete_2 = df_targets_alist[df_targets_alist['Source Name'].isin(list_incomplete_2)]
alist_incomplete_2 = df_list_incomplete_2['Source Name'].unique()

print 'Have only one observations   : %i'%(len(alist_incomplete_1))
print 'Have only two observations   : %i'%(len(alist_incomplete_2))

#Selecting targets with "completed" observations
#list_completed += extra_a_list
df_targets_alist_completed = df_targets_alist[df_targets_alist['Source Name'].isin(list_completed)]
alist_completed_unique = df_targets_alist_completed['Source Name'].unique()

print 'Have at least 3 observations : %i'%(len(alist_completed_unique))
#---------------------------
#Checking distributions of data.

print '------      o      --------'

#---------------------------
#Show distribution on cadence.

df_by_cadence = pd.DataFrame(data=list(df_targets_alist.groupby('Source Name').count()['file']),columns=['count_number'])
df_by_cadence['count'] = 'bump'

if show_details:
    plt.ion()

    plt.figure()
    df_by_cadence.groupby('count_number').count()['count'].plot.bar(color='b')
    plt.title('')
    print df_by_cadence.groupby('count_number').count()


#     plt.figure()
#     df_targets_alist.groupby('Number of samples').count()['file'].plot.bar(color='b')
#     print df_targets_alist.groupby('Number of samples').count()['file']
    plt.subplots(2,2)
    plt.subplot(2,2,1)
    df_targets_alist.groupby('Number of samples').count()['file'].plot.bar(color='k')
    plt.subplot(2,2,2)
    df_targets_alist_completed.groupby('Number of samples').count()['file'].plot.bar(color='b')
    plt.subplot(2,2,3)
    df_list_incomplete_2.groupby('Number of samples').count()['file'].plot.bar(color='g')
    plt.subplot(2,2,4)
    df_list_incomplete_1.groupby('Number of samples').count()['file'].plot.bar(color='r')
    plt.tight_layout()
    print df_targets_alist.groupby('Number of samples').count()['file']

#     plt.figure()
#     df_targets_alist.groupby('mid_Freq').count()['file'].plot.bar(color='b')
#     print df_targets_alist.groupby('mid_Freq').count()['file']
    plt.subplots(2,2)
    plt.subplot(2,2,1)
    df_targets_alist.groupby('mid_Freq').count()['file'].plot.bar(color='k')
    plt.subplot(2,2,2)
    df_targets_alist_completed.groupby('mid_Freq').count()['file'].plot.bar(color='b')
    plt.subplot(2,2,3)
    df_list_incomplete_2.groupby('mid_Freq').count()['file'].plot.bar(color='g')
    plt.subplot(2,2,4)
    df_list_incomplete_1.groupby('mid_Freq').count()['file'].plot.bar(color='r')
    plt.tight_layout()
    print df_targets_alist.groupby('mid_Freq').count()['file']


    plt.subplots(2,2)
    plt.subplot(2,2,1)
    df_targets_alist.groupby('bands_used').count()['file'].plot.bar(color='k')
    plt.subplot(2,2,2)
    df_targets_alist_completed.groupby('bands_used').count()['file'].plot.bar(color='b')
    plt.subplot(2,2,3)
    df_list_incomplete_2.groupby('bands_used').count()['file'].plot.bar(color='g')
    plt.subplot(2,2,4)
    df_list_incomplete_1.groupby('bands_used').count()['file'].plot.bar(color='r')
    print df_targets_alist.groupby('bands_used').count()['file']
    plt.tight_layout()

#---------------------------
#




