#!/usr/bin/env python

import pandas as pd
from argparse import ArgumentParser
import matplotlib.pylab as plt

pd.options.mode.chained_assignment = None  # To remove pandas warnings: default='warn'

parser = ArgumentParser(description="Command line utility for checking the status of spliced L-band data.")
parser.add_argument('filename', type=str, help='Full path and filenmae to read')
parser.add_argument('-d', action='store_true', default=False, dest='show_details',help='Shows details on the bad ones.')
args = parser.parse_args()

#main(args.filename)

filename = args.filename
show_details = args.show_details

#def main(filename):

#---------------------------
# Read in the full "A list" of stars
#
# This comes from the BL database.
#
#---------------------------
master_file = open('/home/obs/logs/target_list_5-50pc.lst')

a_list_master = master_file.read().splitlines()

#---------------------------
# Find the good and bad L-band data by:
# - Reading in the output from spider.
# - Filtering over several parameters to find the "bad data"
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

#---------------------------
# Filtering bad data.

#Check for missing bands (Need to do before checking for the mid_Freq).
df_missing_bands = df3[~df3['file'].str.contains("0001020304050607",na=False)]
df3 = df3[df3['file'].str.contains("0001020304050607",na=False)]

#Check for high resolution data with the bad central frequency.
# The two main frequency resolutions used are -2.7939677238464355e-06 and -2.835503418452676e-06  .
df_bad = df3[~((df3['mid_Freq'] > 1501.4) & (df3['mid_Freq'] < 1501.5))]

df_bad['mid_Freq'] = df_bad['Frequency of channel 1 (MHz)']-2.7939677238464355e-06*df_bad['Number of channels']/2.
df_bad_cf = df_bad[~((df_bad['mid_Freq'] > 1501.4) & (df_bad['mid_Freq'] < 1501.5))]

df4 = df3[~df3.index.isin(df_bad_cf.index)]

df_bad_cf['status'] = 'bad_cf'

#Selection of L band data (hard)
df_bad_fc1 = df4[~((df4['Frequency of channel 1 (MHz)'] > 2251.4647) & (df4['Frequency of channel 1 (MHz)'] < 2251.4649))]

if len(df_bad_fc1):
    df4 = df4[~df4.index.isin(df_bad_fc1.index)]
    df_bad_fc1['status'] = 'bad_fc1'

#Check for correct Number of Samples
df_bad_ns = df4[df4['Number of samples'] != 16 ]
df_bad_ns['status'] = 'bad_ns'

df4 = df4[df4['Number of samples'] == 16 ]

#Check for missing bands that are actually ok (the ones with missing edges, and the ones that are contiguous).
#df_ok_bands = df_missing_bands[df_missing_bands['file'].str.contains("0102030405",na=False)]
#df_missing_bands = df_missing_bands[~df_missing_bands['file'].str.contains("0102030405",na=False)]

ok_bands = pd.core.series.Series([True if df_missing_bands['bands_used'][ii] in '0001020304050607' else False for ii in  df_missing_bands.index ])
ok_bands.index = df_missing_bands.index
df_ok_bands = df_missing_bands[ok_bands]
df4 = pd.concat([df4,df_ok_bands])

df_missing_bands = df_missing_bands[~ok_bands]
df_missing_bands['status'] = 'missing_bands'

#Could Check for correct file size
#Add other checks here.

#Correction of names.
df4['Source Name'] = df4['Source Name'].str.upper()

#Selection of pulsar data
df_pulsar = df4[df4['Source Name'].str.contains("PSR",na=False)]
df4 = df4[~df4['Source Name'].str.contains("PSR",na=False)]

#Selection of stellar data
df_target = pd.concat([df4[df4['Source Name'].str.contains("DEN",na=False)],df4[df4['Source Name'].str.contains("LHS",na=False)],df4[df4['Source Name'].str.contains("HIP",na=False)],df4[df4['Source Name'].str.contains("GJ",na=False)]])

#Check if there is unknown stars.
df_bad_star_name = df4[~df4.index.isin(df_target.index)]
df_bad_star_name['status'] = 'bad_star_name'

#---------------------------
# Group the bad targets.

#Join all bad files for further checking.
df_bad_target_list = pd.concat([df_bad_cf,df_bad_fc1,df_bad_ns,df_bad_star_name,df_missing_bands])

print '------      o      --------'
if df_bad_target_list.shape[0] > 0:
    print 'The bad targets are grouped by:'
    df_status = df_bad_target_list.groupby('status').count()['file']
    print df_status
    print 'To know a distribution for each of the bad dataframes you could do something like:'
    print "df_bad_ns.groupby('Number of samples').count()['file']"

#    print 'The bad targets are grouped by:'

    if show_details:
        print '------      o      --------'
        print 'Some details on these issues are:'
        plt.ion()

        list_of_bads = df_bad_target_list['status'].unique()

        if 'bad_ns' in list_of_bads:
            plt.figure()
            df_bad_ns.groupby('Number of samples').count()['file'].plot.bar(color='r')
            print df_bad_ns.groupby('Number of samples').count()['file']
        if 'bad_cf' in list_of_bads:
            plt.figure()
            df_bad_cf.groupby('mid_Freq').count()['file'].plot.bar(color='r')
            print df_bad_cf.groupby('mid_Freq').count()['file']
        if 'missing_bands' in list_of_bads:
            print 'For the case of missing bands, we have this distribution.'
            print df_missing_bands.groupby('bands_used').count()['file']
        if 'bad_star_name' in list_of_bads:
            print 'This are the bad named stars:\n ', df_bad_star_name['Source Name'].unique()

else:
    print 'Congrats, no bad data found. |-o-|'

print '------      o      --------'

#NOTE: df3 = df4 + df_bad_target_list + df_pulsar

#---------------------------
#Group the df_targets and look for the ones observed 3 times on the same day.
#Also,
#Group the df_targets and look for the ones observed 1 time or 2 times but need 3.
#---------------------------

G_dates = df_target['Gregorian date (YYYY/MM/DD)'].unique()

a_list = []
list_incomplete_1 = []
list_incomplete_2 = []
list_incomplete_4 = []

for G_date in G_dates:
    df_single_date = df_target[df_target['Gregorian date (YYYY/MM/DD)'].str.contains(G_date,na=False)]
    df_single_date_targets = df_single_date.groupby('Source Name').count()['file'] == 3
    df_bool_list = df_single_date_targets.tolist()
    a_list += list(df_single_date_targets[df_bool_list].index.values)

    #check if observed twice
    df_single_date_targets = df_single_date.groupby('Source Name').count()['file'] == 2
    df_bool_list = df_single_date_targets.tolist()
    list_incomplete_2 += list(df_single_date_targets[df_bool_list].index.values)

    #check if observed once
    df_single_date_targets = df_single_date.groupby('Source Name').count()['file'] == 1
    df_bool_list = df_single_date_targets.tolist()
    list_incomplete_1 += list(df_single_date_targets[df_bool_list].index.values)

    #check if observed more than 3 times
    df_single_date_targets = df_single_date.groupby('Source Name').count()['file'] > 3
    df_bool_list = df_single_date_targets.tolist()
    list_incomplete_4 += list(df_single_date_targets[df_bool_list].index.values)

#---------------------------
#Find which of the incomplete observations are from the a_list_master
a_list_incomplete_1 = set(a_list_master) & set(list_incomplete_1)
a_list_incomplete_2 = set(a_list_master) & set(list_incomplete_2)

#Find the ones that have actually been observed 3 times, but have different observing day (one obs are near midnight).
extra_a_list = list(a_list_incomplete_1 & a_list_incomplete_2)
#and the oposite
a_list_incomplete = list(a_list_incomplete_1 ^ a_list_incomplete_2)

#Check for repeating observations of the same star
a_list += extra_a_list
df_a_list = pd.DataFrame(data=a_list,columns=['star_list'])
a_list_unique = list(df_a_list['star_list'].unique())

#Selecting all the targets from the B list
df_targets_blist = df_target[~df_target['Source Name'].isin(a_list_master)]
df_targets_clist =  df_target[df_target['Source Name'].str.contains('_OFF',na=False)]
df_targets_blist = pd.concat([df_targets_blist,df_targets_clist])
b_list = df_targets_blist['Source Name'].unique()

#Selecting all the good targets from the A list
df_targets_alist = df_target[~df_target['Source Name'].isin(b_list)]


#Selecting all the bad targets from the A list
#df_targets_alist = df_target[df_target['Source Name'].isin(a_list_master)]
#df_bad_targets_alist = df_targets_alist[~df_targets_alist['Source Name'].isin(a_list_unique)]

#---------------------------
#

#to check later
stop
if show_details:
    df_targets_alist.groupby('bands_used').count()['file'].plot.bar()

    #If I want all A stars independent of how many times observed or how many nodes were used.
    df_FF_list = df_bad_target_list[df_bad_target_list['Source Name'].isin(a_list_master)]
    df_AAA_list = pd.concat([df_good_targets_alist,df_FF_list])
    df_AAA_list.groupby('bands_used').count()['file'].plot.bar()
    plt.ylabel('counts')
    plt.title('A-stars observed at least once.')


#---------------------------
#Find which ones have been observed multiple times

df_a_list['tmp'] = 'temp column'

star_count  = df_a_list.groupby('star_list').count()['tmp'] > 1
star_bool = star_count.tolist()
multistar_count = df_a_list.groupby('star_list').count()['tmp'][star_bool]




#---------------------------
#Find stars that have been observed more than once but are not from the A-list






'''if __name__ == "__main__":

    parser = ArgumentParser(description="Command line utility for checking the status of spliced L-band data.")
    parser.add_argument('filename', type=str, help='Full path and filenmae to read')
    args = parser.parse_args()

    main(args.filename)
'''

