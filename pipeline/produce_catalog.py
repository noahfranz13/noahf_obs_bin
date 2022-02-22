"""
Prints the contents of a catalog.
Hint: > this into a file.
GBT logic currently expects that the catalog take this form:
- Space delimited
- A header beginning with exactly the string "head" (without quotes)
--- This must contain the receiver name (one of: Rcvr1_2, Rcvr2_3, Rcvr4_6, Rcvr8_10) which indicates the "already-observed" column
- The rest of the file is a list of targets of the form (name, ra, decl, ..., already-observed, ...)
--- Where ... indicates that the already-observed column index is calculated rather than assumed
--- The indexes of the (name, ra, decl) columns ARE assumed to be (0, 1, 2)
- already-observed should be 0 to indicate NOT already-observed
ORBITS looks for a priority column but it doesn't do anything
"""
import argparse
import os

import bldw

from astropy import units
from astropy.time import Time
from astropy.coordinates import SkyCoord

CATALOG_QUERY = """
select name, ra, decl, pm_ra, pm_decl, priority
from bl.target join bl.priority on bl.target.id = bl.priority.target_id
where receiver_id = %s and target_id not in (
    select distinct target_id
    from bl.tag join bl.target_tag on bl.tag.id = bl.target_tag.tag_id join bl.receiver_tag on bl.receiver_tag.tag_id = bl.target_tag.tag_id
    where receiver_id = %s and type = 'cadence')
"""

assert __name__ == '__main__'

conn = bldw.Connection()

parser = argparse.ArgumentParser()
parser.add_argument('receiver')

args = parser.parse_args()
receiver_name = args.receiver
receiver_id = conn.fetch_receiver_by_name(receiver_name).id

now = Time.now()
epoch = Time('J2000.0', format='jyear_str')
catalog = []
catalog.append(['head=name', 'ra', 'dec', receiver_name, 'Priority'])

# This sorts by priority so that the highest is at the top.
targets = sorted(conn.fetchall(CATALOG_QUERY, (receiver_id, receiver_id)), key=lambda t: t[5], reverse=True)
for name, ra, decl, pm_ra, pm_decl, priority in targets:
    if pm_ra and pm_decl:
        coord = SkyCoord(frame='icrs',
                    obstime=epoch,
                    unit=(units.hourangle, units.degree),
                    ra=ra * units.hourangle,
                    dec=decl * units.degree,
                    pm_ra_cosdec=pm_ra * units.mas / units.yr,
                    pm_dec=pm_decl * units.mas / units.yr)
        coord = coord.apply_space_motion(now)
        ra = coord.ra.hourangle
        decl = coord.dec.deg
    catalog.append([name, str(ra), str(decl), '0', str(priority)])
widths = [max(map(len, col)) for col in zip(*catalog)]
print(str(now) + 'Z')
for line in catalog:
    print('     '.join((val.ljust(width) for val, width in zip(line, widths))))
