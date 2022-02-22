from __future__ import division

import redis
import sys
import time, datetime, pytz, calendar

def process_calendar_lines(calendar_lines):
	"""Gets a list of calendar entries for BL's GBT observations
	
	Args:
		The list of lines read from /home/obs/calendar/gbt_scraper.py stdout

	Returns: 
		A list of dictionaries, where each dictionary represnts a calendar entry 
	
	NOTES:
		This script assumes that there are 7 lines (producing 7 keys per dictionary) per calendar entry.
		This was true as of 2018-07-13: /home/obs/calendar/gbt_scraper.py prints a bunch of datapoints
		to stdout representing metadata from each calendar event. Hopefully this doesn't change!

		Here's an example of gbt_scraper's output:
		START:		2018-07-14 11:30
		END:		2018-07-14 17:30
		TYPE:		A
		RECEIVERS:	L, S, X, C
		FREQ (GHz):	1.15 -  1.73,  1.73 -  2.60,  8.00 - 10.00,  3.85 -  8.00
		PI:		Siemion
		FRIEND:		Maddalena,Bonsall		
	"""
	calendar_lines = [line.replace("\n", "").replace("\t", "") for line in calendar_lines]
	calendar_entries = [calendar_lines[i:i+7] for i in range(0, len(calendar_lines), 7)]
	calendar_entries = [{entry.split(":")[0]:"".join(entry.split(":")[1:]) for entry in cal_entry} for cal_entry in calendar_entries]
	return calendar_entries

def obs_end_time(entry):
	"""Parses end time from entry (written as Eastern Time string) and returns its (utc) unix time
        
        Args:
		entry (dict): A dictionary representing a calendar entry
        
	Returns: 
        	The Unix standard time of the entry
	"""
	end_time = entry['END']
	datetime_naive = datetime.datetime.strptime(end_time, "%Y-%m-%d %H%M")
	datetime_eastern = pytz.timezone('US/Eastern').localize(datetime_naive)
	datetime_utc = datetime_eastern.astimezone(pytz.timezone('UTC'))
	return calendar.timegm(datetime_utc.timetuple()) 

def obs_start_time(entry):
	"""Parses start time from entry (written as Eastern Time string) and returns its (utc) unix time
        
        Args:
                entry (dict): A dictionary representing a calendar entry
        
        Returns: 
                The Unix standard time of the entry
        """
	start_time = entry['START']
	datetime_naive = datetime.datetime.strptime(start_time, "%Y-%m-%d %H%M")
        datetime_eastern = pytz.timezone('US/Eastern').localize(datetime_naive)
        datetime_utc = datetime_eastern.astimezone(pytz.timezone('UTC'))
        return calendar.timegm(datetime_utc.timetuple())

if __name__ == '__main__':
	calendar_lines = []
	for line in sys.stdin:
    		calendar_lines.append(line)
	calendar_entries = process_calendar_lines(calendar_lines)
	current_time = time.time()	
	for entry in calendar_entries:
		end_time = obs_end_time(entry)
		if end_time < current_time:
			continue
		else:
			try:
				start_time = obs_start_time(entry)
				if start_time > current_time:
					obs_length_remaining = (end_time - start_time) / 3600
					print ("Next obs length : {} hrs".format(obs_length_remaining))
				else:
					obs_length_remaining = (end_time - current_time) / 3600
					print ("Remaining time in obs : {} hrs".format(obs_length_remaining))
			except:
				obs_length_remaining = (end_time - current_time) / 3600
				print ("Remaining time in obs : {} hrs".format(obs_length_remaining))
			break	
	minimum_space = obs_length_remaining * 2.2	#TODO - get more accurate value for space / time
	r = redis.StrictRedis()
	keys = r.keys("bl_disk_watch://blc*")
	free_space_per_node = {key:r.hget(key, "disk_free") for key in keys}
	hit_warning = False
	for node, space_descriptor in sorted(free_space_per_node.items()):
		if space_descriptor[-1] == "T":
                        free_space = float(space_descriptor[:-1])
                elif space_desciptor[-1] == "M":
                        free_space = float(space_descriptor[:-1]) / 1000.0
                else:
                        print ("WARNING : unrecognized datatype '{}' in node {} disk_free descriptor: {} . Only 'T' (terabytes) currently supported".format(space_descriptor[-1], node, space_descriptor))          
                        break
                if free_space < minimum_space:
                        print ("Warning : node {} has only {}, but needs {} to finish obs".format(node, space_descriptor, minimum_space))
                        hit_warning = True
                else:
                        print ("{} --> {}".format(node, space_descriptor))
	if not hit_warning:
		print ("Disk storage is sufficient for obs")
	else:
		print (R"""
   /.--------------.\
  //                \\
 //                  \\     +-------------------+
|| .-..----. .-. .--. ||    |                   |
||( ( '-..-'|.-.||.-.|-|    |  Disk storage is  |
|| \ \  ||  || |--|_|--|    |  NOT sufficient   |
||._) ) ||  \'-'/|--' ||    |  for obs          |
 \\'-'  `'   `-' `'  //     |                   |
  \\                //      +-------------------+
   \\______________//
    '--------------'
          |_|_
   ____ _/ _)_)
       '  | (_)
    .--'"\| ()
          | |
          | |
          |_|
""")
		sys.exit(1)





