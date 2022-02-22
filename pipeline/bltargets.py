#!/usr/bin/env python
"""
The bltargets module is a library to help interact with the BLtargets database.
"""
from astropy.time import Time
from datetime import datetime, timezone
import MySQLdb
import os
import sys
import time

from cadence import Cadence

def timestamp_from_h5(h5file):
    tstart = h5file["data"].attrs["tstart"]
    time = Time(tstart, format="mjd")
    return time.unix

class Scan(object):
    """
    A Scan represents one object in the go_scans database.
    """
    def __init__(self, row):
        (self.id, self.session, self.target_name, self.utc_observed, self.receiver, self.ra_hrs,
         self.dec_deg, self.azimuth, self.elevation, self.skyfreq, self.restfreq, self.observer,
         self.target_id) = row
        self.utc_observed = self.utc_observed.replace(tzinfo=timezone.utc)

    def timestamp(self):
        return int(self.utc_observed.timestamp())

    @staticmethod
    def is_cadence(scans):
        """
        We heuristically check target names because the original cadence intention is not recorded in the database.
        """
        if len(scans) != 6:
            return False
        target_name = scans[0].target_name
        for i in (2, 4):
            if scans[i].target_name != target_name:
                return False
        for i in (1, 3, 5):
            if scans[i].target_name == target_name:
                return False
        return True
        
    
    def __str__(self):
        return f"id = {self.id}, session = {self.session}, utc = {self.utc_observed.strftime('%Y-%m-%d %X')}, target = {self.target_name}"

    
class Connection(object):
    """
    Open a connection to BLtargets.
    """
    def __init__(self):
        self.connect()
        
    def connect(self):
        retries = 10
        for _ in range(retries):
            try:
                self.conn = MySQLdb.connect(host="104.154.94.28", user="aw24576", db="BLtargets")
                return
            except MySQLdb.OperationalError as e:
                print(f"mysql connection error: {e}")
                time.sleep(10)
        raise IOError(f"mysql connection failed even after {retries} retries")

    def fetchall(self, command, args=()):
        cur = self.conn.cursor()
        cur.execute(command, args)
        result = cur.fetchall()
        cur.close()
        return result

    def fetch_scans_where(self, where, args=()):
        command = "SELECT * FROM go_scans WHERE " + where
        rows = self.fetchall(command, args=args)
        return [Scan(row) for row in rows]

    def fetch_scans_for_session(self, session):
        return self.fetch_scans_where("session = %s", args=(session,))
    
    def guess_scan(self, h5file):
        """
        Guesses which scan corresponds to an h5 file.
        We heuristically check for a scan that starts at about the same time, and double-check
        that the information we find matches the filename.
        Raises a LookupError if our heuristics don't work.
        """
        filename = os.path.normpath(h5file.filename)
        timestamp = timestamp_from_h5(h5file)
        error_margin = 20 # seconds
        scans = self.fetch_scans_where("abs(unix_timestamp(utc_observed) - %s) <= %s", (timestamp, error_margin))
        if len(scans) > 1:
            raise LookupError("multiple scans matched:\n" + "\n".join(map(str, scans)))
        if not scans:
            raise LookupError(f"no scan is close to file start time {timestamp}")
        scan = scans[0]
        if scan.session not in filename:
            raise LookupError(f"db session {scan.session} doesn't match filename: {filename}")
        if scan.target_name not in filename:
            raise LookupError(f"db target {scan.target_name} doesn't match filename: {filename}")
        return scan

    def scans_before(self, timestamp, n):
        """
        Returns the n scans before this timestamp.
        """
        scans = self.fetch_scans_where("unix_timestamp(utc_observed) <= %s ORDER BY utc_observed DESC LIMIT %s", (timestamp, n))
        return list(reversed(scans))

    def scans_after(self, timestamp, n):
        """
        Returns the n scans after this timestamp.
        """
        scans = self.fetch_scans_where("unix_timestamp(utc_observed) >= %s ORDER BY utc_observed LIMIT %s", (timestamp, n))
        return scans
    
    def fetch_scan(self, scan_id):
        scans = self.fetch_scans_where("id = %s", (scan_id,))
        if not scans:
            raise LookupError(f"no scan with id {scan_id}")
        if len(scans) > 1:
            raise RuntimeError(f"found {len(scans)} scans with id {scan_id}")
        return scans[0]

    def fetch_cadences_for_session(self, session):
        scans = self.fetch_scans_for_session(session)
        return Cadence.find_cadences(scans)

    def fetch_cadence(self, cadence_id):
        assert type(cadence_id) == int
        # We need to know the session to create cadences, and the cadence id is just the id
        # of the first scan in the cadence, so fetch the scan first.
        scan = self.fetch_scan(cadence_id)
        cadences = self.fetch_cadences_for_session(scan.session)
        for cadence in cadences:
            if cadence.id == cadence_id:
                return cadence
        raise LookupError(f"no cadence for id {cadence_id}")
    
    
if __name__ == "__main__":
    # Look up data for a bunch of scan ids
    c = Connection()
    for arg in sys.argv[1:]:
        scan_id = int(arg)
        scan = c.fetch_scan(scan_id)
        print(scan)
