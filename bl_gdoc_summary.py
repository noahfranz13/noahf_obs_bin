#/usr/bin/python

'''
   bl_gdoc_summary.py
   
   Purpose: Read the Targets database, summarize the stars that we already 
            have observed and send them to a Google spreadsheet.
            Set a Cronjob to update the document every day.
            
    Author: H. Isaacson
    
    Date: April 2017
          Updated 2018 Mar 7

    Known Issues: 
          Sometimes new rows need to be added before it will run properly.
          Automatically adding rows needs to be added to this program.
          The number of cells that be be added or read in one command
          is limited to some 50,000 or so cells. Divide and conquer
'''

import os
import MySQLdb 
import pandas as pd
from pandas import DataFrame
from pandas import Series
import gspread
from df2gspread import df2gspread as d2g

#  Link/open Google spreadsheet.
from oauth2client.service_account import ServiceAccountCredentials
scope = ['https://spreadsheets.google.com/feeds',
                  'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('/home/obs/.credentials/cloud_credential_27mar2018.json', scope)

gc = gspread.authorize(credentials)
sh = gc.open('Breakthrough Listen GBT Log')
# End google interaction, until below.

def RAdeg2dms_str(radeg):
    # Use the factor of 15 if converting from degrees.
    #radeg = radeg / 15. # convert from degrees to Hours
    mnt,sec = divmod(radeg*3600,60) # convert hours to seconds and divide by 60
    rahr,mnt = divmod(mnt,60)  # convert minutes to divide by 60  
    #print radeg,mnt,sec
    if rahr >= 10:
        hr = str(int(rahr))
    else:
        hr = "0"+str(int(rahr))
    if mnt >= 10:
       min = str(int(mnt))
    else:
        min = "0"+str(int(mnt))
#    if round(sec) >= 10:
    if sec >= 10:
        sec = str(round(sec,1))
    else:
        sec = "0"+str(int(sec))
    ra_str = hr + ":" + min + ":" + sec
    return ra_str

def decdeg2dms_str(dd):  # Create sexigesimal Declination from decimal.
    if dd < 0:
       sgn = '-'
    else:
       sgn = ''
    mnt,sec = divmod(abs(dd)*3600,60) #convert degrees to seconds,divide by 60
    deg,mnt = divmod(mnt,60)
    if deg >= 10: 
       decd = str(int(deg))
    else:
      decd = "0"+str(int(deg))
    if mnt >= 10 :
      mnt = str(int(mnt))
    else:
      mnt = "0"+str(int(mnt))
    if sec >= 10:
      sec = str(round(sec,1))
    else:
      sec = "0"+str(int(sec))
    dec_str = sgn+decd+":" +mnt+ ":" +sec
    return dec_str



# Open connection to SQL server and a cursor. Only need read-only
#db = MySQLdb.connect("104.154.94.28","root","","BLtargets" ) # pword removed.
db = MySQLdb.connect("104.154.94.28","interns","FZtjWD3B4Yv5aq3m","BLtargets" ) #read only
cursor = db.cursor()

sql_com1 = '''SELECT target, receiver, date FROM go_observations'''
cursor.execute(sql_com1)
sql_out1 = cursor.fetchall()
output1 = list(sql_out1)

indx1 = ['name','rec','date']
df1 = DataFrame(output1,columns = indx1) 
df1['rec']=df1['rec'].str.strip() # Trip extra spaces

# Separate total observations by receiver.
df1_lband = df1[df1['rec'] == 'Rcvr1_2']
df1_sband = df1[df1['rec'] == 'Rcvr2_3']
df1_cband = df1[df1['rec'] == 'Rcvr4_6']
df1_xband = df1[df1['rec'] == 'Rcvr8_10']
df1_kband = df1[df1['rec'] == 'RcvrArray18_26']
#recs = ['Rcvr1_2','Rcvr2_3','Rcvr4_6','Rcvr8_10']
                
# PUll the A -list, Blist and Galaxy list out of the SQL table.
#   A-list: P for primary, Blist S for secondary. G = galaxy. other = O

# GATHER A LIST STARS, full list
sql_com2 = '''SELECT * FROM `object_five_50_pc_sample` ORDER BY `RA_dec_hrs` ASC'''
cursor.execute(sql_com2)
sql_out2 = cursor.fetchall()
output2 = list(sql_out2)
indx2 = ['target_id','name','RA_sexagesimal','DECL_sexigesimal', 'Equinox','Vmag','Sp_type','dist','star_id','star_id_str','RA_dec_hrs', 'DECL_dec_deg']
df2 = DataFrame(output2,columns = indx2)
df1_Alist = df2.merge(df1,on='name',how = 'inner')
del df2['RA_sexagesimal']
del df2['DECL_sexigesimal']

# GATHER B LIST STARS
sql_com3 = '''SELECT target_id,name,RA_dec_hrs,DECL_dec_deg  FROM `object_blist` ORDER BY `RA_dec_hrs` ASC'''
cursor.execute(sql_com3)
sql_out3 = cursor.fetchall()
output3 = list(sql_out3)
indx3 = ['target_id','name','RA_dec_hrs','DECL_dec_deg']
df3 = DataFrame(output3,columns = indx3)
df1_Blist = df3.merge(df1,on='name',how = 'inner')

# GATHER Galaxies, currently 869, not the 125 from Targets paper.
sql_com4 = '''SELECT name, RA_dec_hrs,DECL_dec_deg,class FROM `object_nearest_galaxies` '''
cursor.execute(sql_com4)
sql_out4 = cursor.fetchall()
output4 = list(sql_out4)
indx4 = ['name','RA_dec_hrs','DECL_dec_deg','class']
df4 = DataFrame(output4,columns=indx4 )
df1_gal=df4.merge(df1,on='name',how = 'inner')
cursor.close()
db.close()


# Next construct the DataFrame that will be uploaded to the google doc

col1 = set(df1['name'])
Lband_obs = []

#RE-read the Alist and extract name, sptype and distance
indx2_a = ['name','Sp_type','dist']
df2_3col = pd.DataFrame(df2,columns = indx2_a)
df2_3col=df2_3col.sort_values('name')

indx5 = ['Star','Name','RA','Dec','Epoch','Vmag','SpType', 'Distance(pc)','PM_RA','PM_Dec']

#file_in = 'alist_enriquez2017.txt'
#df5 = pd.read_csv(file_in,names = ['name'])
#lenA = len(df5)
#df2_A = DataFrame(output2,index = df5.starname)

# Add columns that have RA, Dec, Sptype, Distance, and whatever else.
#df2_A = df5.merge(df2_3col,how='left')

# Cross refernece the list of galaxies vs the list of what's been observed.

df_gal_all= df4.merge(df1,on='name',how='left') #keep every galaxy, combine with what is observed
df_gal_observed=df_gal_all.dropna(axis=0,how='any') # drop any galaxies not observed

# A list stars
df_Astar_all = df2.merge(df1,on='name',how='left')
df_Astar_observed = df_Astar_all.dropna(axis=0,how='any')

# B list stars 
df_Bstar_all = df3.merge(df1,on='name',how='left')
df_Bstar_observed = df_Bstar_all.dropna(axis=0,how='any')

# Find number of A, B and Galaxies observed at each band.
print "Number of Alist stars observed,L-band: ",len(df1_lband.merge(df1_Alist,on='name',how='inner').drop_duplicates('name'))
print "Number of Alist stars observed,S-band: ",len(df1_sband.merge(df1_Alist,on='name',how='inner').drop_duplicates('name'))
print "Number of Alist stars observed,C-band: ",len(df1_cband.merge(df1_Alist,on='name',how='inner').drop_duplicates('name'))
print "Number of Alist stars observed,X-band: ",len(df1_xband.merge(df1_Alist,on='name',how='inner').drop_duplicates('name'))

print "Number of Blist stars observed,L-band: ",len(df1_lband.merge(df1_Blist,on='name',how='inner').drop_duplicates('name'))
print "Number of Blist stars observed,S-band: ",len(df1_sband.merge(df1_Blist,on='name',how='inner').drop_duplicates('name'))
print "Number of Blist stars observed,C-band: ",len(df1_cband.merge(df1_Blist,on='name',how='inner').drop_duplicates('name'))
print "Number of Blist stars observed,X-band: ",len(df1_xband.merge(df1_Blist,on='name',how='inner').drop_duplicates('name'))

print "Number of Galaxies stars observed,L-band: ",len(df1_lband.merge(df1_gal,on='name',how='inner').drop_duplicates('name'))
print "Number of Galaxies stars observed,S-band: ",len(df1_sband.merge(df1_gal,on='name',how='inner').drop_duplicates('name'))
print "Number of Galaxies stars observed,C-band: ",len(df1_cband.merge(df1_gal,on='name',how='inner').drop_duplicates('name'))
print "Number of Galaxies stars observed,X-band: ",len(df1_xband.merge(df1_gal,on='name',how='inner').drop_duplicates('name'))

                                                    

# All objects not in Galaxy, Astar, Bstar lists
names_gab = pd.concat([df_gal_observed['name'],df_Astar_observed['name'],df_Bstar_observed['name']])
ra_gab = pd.concat([df_gal_observed['RA_dec_hrs'],df_Astar_observed['RA_dec_hrs'],df_Bstar_observed['RA_dec_hrs']])
dec_gab = pd.concat([df_gal_observed['DECL_dec_deg'],df_Astar_observed['DECL_dec_deg'],df_Bstar_observed['DECL_dec_deg']])
obs_n_r_d = pd.concat([names_gab,ra_gab,dec_gab],axis=1)


#Create a .csv, which can be copied to a spreadsheet, later hook directly into spreadsheet.
sh_labels = ['Name','Right Ascension','Declination','L-band','S-band'
            ,'C-band','X-band']
df_sh = DataFrame(columns = sh_labels)
df_sh['Name']=names_gab.drop_duplicates()#'name')['name']

# Iterate thorugh each unique object and add either nothing, or the date if observed in that band.

# Please change this crap programming to somehting more efficient.
recs = ['Rcvr1_2','Rcvr2_3','Rcvr4_6','Rcvr8_10']
for i,item in enumerate(df_sh['Name']):
# Add in right ascension/ Declination, Cross check, A list, Blist, Galaxies
    target1 = obs_n_r_d[obs_n_r_d['name'] ==item]
    target2 = target1.drop_duplicates()
    df_sh['Right Ascension'].iloc[i] = target2['RA_dec_hrs'].iloc[0]
    df_sh['Declination'].iloc[i] = target2['DECL_dec_deg'].iloc[0]
    target = df1[df1['name'] == item] #indx is all entries for that target
    #indx = ind[0] # it may have multiple instances, start iwth the first
    for j,jitem in enumerate(target['rec']):
        if jitem == recs[0]:
           df_sh['L-band'].iloc[i] = target['date'].iloc[j]
        if jitem == recs[1]:
           df_sh['S-band'].iloc[i] = target['date'].iloc[j]
        if jitem == recs[2]:
           df_sh['C-band'].iloc[i] = target['date'].iloc[j]
        if jitem == recs[3]:
           df_sh['X-band'].iloc[i] = target['date'].iloc[j]

           
# Create output file            
#outname = '/home/hisaacson/logs/GBT_google_log.csv'
#df_sh.to_csv(outname,index=False)

df_sh = df_sh.fillna('--') # Use this above to_csv is NaN values are causing a problem.

# Try to add to google doc using gspread commands
worksheet = sh.worksheet('A worksheet')

#worksheet.update_cells(cell_list)
#Determine range of cells to select:
#rng = A3:G(N_objects+3)
hdr_row = 2
ncol = 7
ncol_char = chr(65+ncol-1)
nrow = len(df_sh)
rng = 'A3:G'+str(nrow+hdr_row) # Start at A3 to leave room for header
cell_list = worksheet.range(rng)

outlist = []
#outlist.append(df_sh['Name'].value)
indx=0
#df_sh = df_sh.iloc[0:100] for testing.
for item in df_sh['Name']:
    cell_list[indx*ncol].value = df_sh.iloc[indx,0]
    cell_list[indx*ncol+1].value =  str(df_sh.iloc[indx,1])
    cell_list[indx*ncol+2].value = str(df_sh.iloc[indx,2])
    cell_list[indx*ncol+3].value = str(df_sh.iloc[indx,3]) #Must go to string for json formatting
    cell_list[indx*ncol+4].value = str(df_sh.iloc[indx,4])    
    cell_list[indx*ncol+5].value = str(df_sh.iloc[indx,5])
    cell_list[indx*ncol+6].value = str(df_sh.iloc[indx,6])
#    print indx
#    cell_list.append(df_sh.iloc[indx,:])
    indx += 1


#worksheet.update_cells(cell_list)
print "The google doc has been updated"

# Next produce some useful data frames:

# X-band pulsars that have been observed:
df1_xband_unique = df1_xband.drop_duplicates('name')
xband_pulsars = df1_xband_unique[df1_xband_unique['name'].str.contains('PSR')]


# df_sh=df_sh.merge(df_temp,left_on='Name',right_on='name')#,lsuffix='l',rsuffix='r') # from Astars 
# del df_sh['name']
# 
# #mv values from one colulmn to another
# df_sh['Right Ascension']= df_sh['RA_dec_hrs']
# df_sh['Declination'] = df_sh['DECL_dec_deg']
# del df_sh['RA_dec_hrs']
# del df_sh['DECL_dec_deg']
# 
# 
# # Try to populate the L-band observed targets with the date.
# #temp = df_sh['rec'].isin()
# #
# #for i,item in enumerate(df_sh['Name']):
# #   
# #   ind=df1.name == item
# #   obsdate = df1['date'].iloc[ind]
# #   df_sh['L-band'] = obsdate
# 
# # For name of star in df_sh, look in df2 and if receiver = Rcvr1_2 then Lband = date
# rec1 = 'Rcvr1_2' # Stupid spaces, Think of better way to remove them.
# rec2 = 'Rcvr2_3'
# rec3 = 'Rcvr4_6'
# rec4 = 'Rcvr8_10'
# 
# 



