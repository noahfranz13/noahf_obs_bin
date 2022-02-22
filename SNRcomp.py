#!/usr/bin/env python

import os,sys
import pandas as pd
import call_observer
# ----- Config ----- #
Np=2
Ttime = 5*60 # In seconds
Wfrac = 5 # Assuming 5% pulse width
mW = 0.05 # Fraction of number of channels used for median estimation for zapping
csvfile = "/home/obs/target_logs/PULSARS"
#csvfile="test.csv"
# ------------------ # 

filfile = sys.argv[1]
fname = filfile.split('/')[-1].strip('.fil')

#Get Session ID
SessionID='*'
tmp = "_".join(fname.split("_")[1:4])
if tmp[:4] == "AGBT": SessionID=tmp

#print SessionID

#Read CSV file
csvdata = pd.read_csv(csvfile)

cmd="echo %s | sed 's/Psr/PSR/' | sed 's/psr/PSR/' | awk -F_PSR_ '{print $2}' | awk -F_ '{print $1}' | sed 's/j/J/' | sed 's/b/B/'" % (filfile)
PSRNAME=os.popen(cmd).readline().strip()

#print PSRNAME

cmd="psrcat -e %s > tmp.par" % (PSRNAME)
os.system(cmd)

cmd="dspsr -E tmp.par %s -O %s" % (filfile,fname)
os.system(cmd)

#cmd="paz -r -L -b -d -m %s.ar" % (fname)
cmd="psredit -c 'nchan' %s.ar  | awk -F= '{print$2}'" % (fname)
nchans=int(os.popen(cmd).readline().strip())

cmd="paz -r -R %d -L -b -d -m %s.ar > out " % (int(nchans*mW),fname)
os.system(cmd)

#Get number of RFI zapped channels
cmd="grep 'paz -z' out | awk -F-z '{print$2}' | awk '{print NF}'"
rfichan=int(os.popen(cmd).readline().strip())
os.system("rm out")

cmd="psrstat -jDF -c 'snr=modular:{on=minimum:{find_min=0,smooth:width=0.05}}' -c snr %s.ar " % (fname)
SNR=float(os.popen(cmd).readline().strip().split("=")[1])

#Off pulse rms
cmd="psrstat -jDF -c 'snr=modular:{on=minimum:{find_min=0,smooth:width=0.05}}' -c off:rms %s.ar" % (fname)
RMS=float(os.popen(cmd).readline().strip().split("=")[1])

#Center frequency
#FREQ = pfdfl.lofreq - 0.5*pfdfl.chan_wid + pfdfl.chan_wid*(pfdfl.numchan/2)
cmd="psredit -c freq %s.ar" % (fname)
FREQ=float(os.popen(cmd).readline().strip().split("=")[1])

cmd="psredit -c bw %s.ar" % (fname)
BW=float(os.popen(cmd).readline().strip().split("=")[1])
BWMHz = BW
BW=abs(BW*pow(10,6)) # In Hz

if rfichan>1:
	BW=BW-rfichan*(BW/nchans)	

#Get MJD
cmd = "header %s -tstart" % (filfile)
MJD = float(os.popen(cmd).readline().strip())

BWfact = 0.9

#SEFD
if FREQ<2000: 
	SEFD = 10 # For GBT-L band
	BWfact = 0.6  # For GBT-BL only uses about 60% of the band (considering RFI rejection and bandshape)
if FREQ>2000 and FREQ<3000: 
	SEFD = 12 # GBT-S band
	BWfact=0.75 # GBT-BL S-band with notch filter and RFI rejection
if FREQ>3000 and FREQ<8000: SEFD = 10 # GBT-C band
if FREQ>8000 and FREQ<12000: SEFD = 15 # GBT-X band
if FREQ>12000 and FREQ<18000: SEFD = 15 # GBT Ku-band
if FREQ>18000 and FREQ<26000: SEFD = 25 # GBT KFPA-band
if FREQ>26000: raise ValueError('Need SEFD value for FREQ>26 GHz.')

#Only for 80% of the band, we have sufficient sensitivity. 
BW = BWfact*BW

# Get spectral index
cmd="psrcat -c 'SPINDX' -o short -nohead -nonumber " + str(PSRNAME) + " 2>&1 "
SPINDEX=os.popen(cmd).readline().strip()

# If not in the catalogue, then assume -1.4 (Bates et al. 2013)
if SPINDEX=="*": SPINDEX=-1.4
else: SPINDEX=float(SPINDEX)

# Flux at 1400 MHz
cmd="psrcat -c 'S1400' -o short -nohead -nonumber " + str(PSRNAME) + " 2>&1 "
S1400=float(os.popen(cmd).readline().strip())

#Flux at the observing frequency
FLUX=S1400*pow((FREQ/1400.0),SPINDEX)

#Expected average profile SNR
expSNR = FLUX * pow(10,-3) * pow(Np*Ttime*BW,0.5) / (1.16*SEFD)

print PSRNAME
print SessionID
print "Flux at 1400 MHz : " + str(S1400) + " mJy"
print "Flux at " + str(FREQ)  + " MHz : " + str(FLUX) + " mJy"
print "Expected SNR : " + str(expSNR)
print "Observed SNR : " + str(SNR)

#Place holder right now
detection="*"

if SNR>expSNR:
	detection="1"
elif (expSNR-SNR)/expSNR<0.75: #If the difference was around 75% level of the expected flux
	detection="1"

if not sys.stdin.isatty():
  if detection == "1":
    message = "SNRcomp: :white_check_mark: Pulse detected :pulsar:"
  else:
    message = "SNRcomp: :rotating_light: Pulse NOT detected! You might want to check things out..."
    call_observer.call_observer("The canary script failed to detect the pulsar. Please check the plots in Slack.")
  os.system("/usr/bin/redis-cli -h bl-head publish astrid '" + message + "'")

#pdiff = abs((expSNR-SNR)/SNR)

# Append current csv database
d = [SessionID,PSRNAME,MJD,FREQ,BWMHz,expSNR,SNR,detection]
d = pd.DataFrame([d],columns=list(csvdata.keys()))
csvdata = csvdata.append(d,ignore_index=True)
os.system("/home/obs/bin/redis_canary")

#Write to output
csvdata.to_csv(csvfile,index=False)

cmd = "psrplot -N 1x2 -p flux -p freq  " + \
      " -j :0:dedisperse -j :0:fscrunch -j ':1:dedisperse' -j :0:C -j :1:C " + \
      " -c ':0:set=pub,below:r=Obs SNR: %.2f'" % (float(SNR)) +  \
      " -c ':0:below:l=Expected SNR: %.2f'" % (float(expSNR)) + \
      " -c ':1:set=pub,above:c= ,ch=2,y:reverse=1' " + \
      " -c ':0:above:c=%s'  " % (PSRNAME) + \
      " -D  %s_DSPSR.png/png " % (fname) + \
      " -c ':1:y:view=(0.1,1.13)' %s.ar " % (fname) 

print cmd	
os.system(cmd)


