#!/usr/bin/env python
"""
The bldw module is a library to help you connect to the bldw database.

To run this on your own machine you need to set up the appropriate auth files in this directory.

bldw.ini
This file contains auth information with these specific lines:
host=<35.232.16.28
database=bldw_data
user=<your_user>
password=<your_password>
connect_timeout=5

Any extra postgres parameters you want can be stuck in there too.

You also need the SSL cert stuff:
server-ca.pem
client-cert.pem
client-key.pem

If these names are confusing, go look at some Google Cloud documentation to see what they all are.
"""
from astropy.time import Time
from datetime import datetime
from cadence import Cadence
import machines
import math
import os
import psycopg2
import sys
import time

DIR = os.path.dirname(os.path.realpath(__file__))

# A list of (fine channels per coarse channel, foff) pairs to use for guessing coarse channels.
# We just store absolute foff value since the resolution guess is the same for positive or negative.
GB_RESOLUTIONS = [
    (8, 0.3662109375),
    (16, 0.18310546875),
    (32, 0.091552734375),
    (1024, 0.00286102294921875),
    (999424, 2.9313759725601946e-06),
    (1033216, 2.835503418452676e-06),
    (1048576, 2.7939677238464355e-06),
]

INVALID_CADENCE_TARGETS = set([
    # calibrators
    52574, # 3C123
    57688, # 3C286
    67831, # 3C147
    76532, # 3C48
    82906, # 3C196
    92534, # 3C295
    # TSYS
    96846, # TSYS_BTL
])

def approx_eq(f1, f2):
    return abs(f1 - f2) < 0.00001

def mult_approx_eq(f1, f2):
    # Approximately equal in a multiplicative sense, so it knows that 0.00001 and 0.00002 are super different
    try:
        log_rat = math.log(f1 / f2)
    except ValueError:
        return False
    return approx_eq(log_rat, 0)

def timestamp_from_h5(h5file):
    tstart = h5file["data"].attrs["tstart"]
    time = Time(tstart, format="mjd")
    return time.unix

class Metadata(object):
    """
    A Metadata object represents one entry in bl.data describing the data in a single file.
    """
    @classmethod
    def from_h5(cls, h5file, observation_id):
        meta = cls()
        filename = h5file.filename
        meta.id = None
        meta.observation_id = observation_id
        assert filename.endswith(".h5")
        meta.format = "hdf5"
        meta.location = machines.to_location(filename)
        meta.deleted = False
        meta.size = os.path.getsize(filename)
        data = h5file["data"]
        attrs = data.attrs

        # Most database fields are just copied from file headers
        meta.fch1 = attrs["fch1"].item()
        meta.foff = attrs["foff"].item()
        meta.nchans = attrs["nchans"].item()
        meta.nbits = attrs["nbits"].item()
        meta.tstart = attrs["tstart"].item()
        meta.tsamp = attrs["tsamp"].item()
        meta.nifs = attrs["nifs"].item()
        meta.nsamples = data.shape[0]

        # We have to guess the number of coarse channels.
        # This only works for Green Bank, so we double-check this is a Green Bank file.
        telescope_id = attrs["telescope_id"].item()
        assert telescope_id == 6
        for fine_per_coarse, standard_foff in GB_RESOLUTIONS:
            if not mult_approx_eq(standard_foff, abs(meta.foff)):
                continue
            if meta.nchans % fine_per_coarse != 0:
                raise ValueError("this file appears to contain an incomplete coarse channel")
            meta.coarse_channels = meta.nchans // fine_per_coarse
            if meta.coarse_channels > 4096:
                raise ValueError(f"sanity check failed: num coarse channels of {meta.coarse_channels} is too high")
            break
        else:
            raise ValueError(f"unexpected foff: {meta.foff}")
            
        # calculate freq_low and freq_high for convenience
        start = meta.fch1 - (meta.foff / 2)
        end = start + (meta.nchans * meta.foff)
        if meta.foff > 0:
          meta.freq_low = start
          meta.freq_high = end
        else:
          meta.freq_low = end
          meta.freq_high = start

        return meta

    @classmethod
    def from_row(cls, row):
        meta = cls()
        (meta.id, meta.observation_id, meta.format, meta.size, meta.freq_low, meta.freq_high,
         meta.location, meta.deleted, meta.coarse_channels, meta.fch1, meta.foff, meta.nbits,
         meta.tstart, meta.tsamp, meta.nsamples, meta.nchans, meta.nifs) = row
        return meta

    def datacenter(self):
        dc, _ = machines.from_location(self.location)
        return dc

    def filename(self):
        _, filename = machines.from_location(self.location)
        return filename

    def session(self):
        parts = self.location.split("/")
        for part in parts:
            if part.startswith("AGBT"):
                return part
        raise ValueError(f"could not extract session from string: {self.location}")
    
    def __str__(self):
        answer = f"{self.location} | {self.strtime()}"
        if self.deleted:
            answer += " (deleted)"
        return answer

    def same_data(self, other):
        """
        Returns whether these two Metadata objects appear to refer to the same data,
        kept in different locations.
        """
        if self.format != other.format:
            return False
        if not approx_eq(self.freq_low, other.freq_low):
            return False
        if not approx_eq(self.freq_high, other.freq_high):
            return False
        if round(self.tstart) != round(other.tstart):
            return False
        if self.nsamples != other.nsamples:
            return False
        if self.nchans != other.nchans:
            return False
        if self.size != other.size:
            return False
        if self.coarse_channels != other.coarse_channels:
            raise ValueError("coarse channels should not mismatch if the rest of the data matches")

        return True

    def dat_exists(self):
        # This is generated when the turboseti phase completes
        if not os.path.exists(self.dat_filename()):
            return False
        if os.path.getsize(self.dat_filename()) == 0:
            return False
        return True
        
    def can_be_aligned(self):
        """
        Check whether this file is a candidate for aligning into a cadence.
        """
        # We need the h5 to find events
        if self.deleted:
            return False
        # We only run event phase in Berkeley
        if self.datacenter() != machines.BERKELEY:
            return False
        # This is heuristic, but for now, we only look for events for files of this precise shape
        return self.nchans == 67108864 and self.nsamples == 16

    def representative_freq(self):
        return int(self.freq_high)

    def has_freq(self, freq):
        return self.freq_low <= freq <= self.freq_high

    def dat_filename(self):
        """
        The path to the .dat file that the turboseti phase generates for this file.
        """
        if self.datacenter() != machines.BERKELEY:
            raise RuntimeError("there is no dat filename for files outside of Berkeley")
        part = self.filename().split("pipeline/", 1)[-1]
        assert part.endswith(".h5")
        session_to_number = part[:-3]
        base = session_to_number.rsplit("/", 1)[-1]
        return f"/home/obs/turboseti/{session_to_number}/{base}.dat"

    def last_dir(self):
        """
        The last directory this file is in. Awkwardly, this sometimes has bank information.
        """
        return self.location.split("/")[-2]
    
    def timestamp(self):
        time = Time(self.tstart, format="mjd")
        return round(time.unix)

    def strtime(self):
        dt = datetime.utcfromtimestamp(self.timestamp())
        return str(dt)

    
class Receiver(object):
    """
    A Receiver object represents the data around one receiver.
    """
    @classmethod
    def from_row(cls, row):
        rec = cls()
        (rec.id, rec.name, rec.telescope, rec.beam_width) = row
        return rec


class Target(object):
    """
    A Target object represents the data around one thing in the sky you can look at, like Jupiter or TIC238597.
    """
    @classmethod
    def from_row(cls, row):
        target = cls()
        (target.id, target.name, target.ra, target.decl, target.pm_ra, target.pm_decl, target.epoch) = row
        return target

    @classmethod
    def from_vals(cls, id, name, ra, decl, pm_ra, pm_decl, epoch):
        target = cls()
        target.id = id
        target.name = name
        target.ra = ra
        target.decl = decl
        target.pm_ra = pm_ra
        target.pm_decl = pm_decl
        target.epoch = epoch
        return target

    def __str__(self):
        return f"{self.id}, {self.name}, {self.ra}, {self.decl}, {self.pm_ra}, {self.pm_decl}, {self.epoch}"

class Tag(object):
    """
    A Tag object represents the definition of a tag that can be applied (via an intermediate table) to an observation or data row.
    """
    @classmethod
    def from_row(cls, row):
        tag = cls()
        (tag.id, tag.name, tag.description, tag.type) = row
        return tag

class Observation(object):
    """
    An Observation object represents the data for one observation.
    """
    @classmethod
    def from_row(cls, row):
        ob = cls()
        (ob.id, ob.ra, ob.decl, ob.receiver_id, ob.start_time, ob.duration, ob.target_id) = row
        return ob

    @classmethod
    def from_vals(cls, id, ra, decl, receiver_id, start_time, duration, target_id):
        ob = cls()
        ob.id = id
        ob.ra = ra
        ob.decl = decl
        ob.receiver_id = receiver_id
        ob.start_time = start_time
        ob.duration = duration
        ob.target_id = target_id
        return ob

    @classmethod
    def from_scan(cls, scan, conn):
        ob = cls()
        ob.id = scan.id
        ob.ra = scan.ra_hrs
        ob.decl = scan.dec_deg
        ob.receiver_id = conn.fetch_receiver_by_name(scan.receiver).id
        ob.start_time = int(scan.utc_observed.timestamp())
        # Our data pipeline currently drops the duration before it hits go_scans, so
        # just leave it null here.
        ob.duration = None
        return ob

    def timestamp(self):
        return self.start_time

    def strtime(self):
        dt = datetime.utcfromtimestamp(self.timestamp())
        return str(dt)
    
    @staticmethod
    def is_cadence(obs):
        """
        obs is a list of observation objects.
        We heuristically check target ids because the original cadence intention is not recorded in the database.
        """
        if len(obs) != 6:
            return False
        if len(set(o.receiver_id for o in obs)) != 1:
            return False
        target_ids = [o.target_id for o in obs]
        if len(INVALID_CADENCE_TARGETS.intersection(set(target_ids))) > 0:
            return False
        # check ABACAD
        primary = obs[0].target_id
        matches = [i for i, target_id in enumerate(target_ids) if primary == target_id]
        non_matches = [i for i, target_id in enumerate(target_ids) if primary != target_id]
        if matches == [0, 2, 4] and non_matches == [1, 3, 5]:
            return True
        # check BACADA
        primary = obs[1].target_id
        matches = [i for i, target_id in enumerate(target_ids) if primary == target_id]
        non_matches = [i for i, target_id in enumerate(target_ids) if primary != target_id]
        if matches == [1, 3, 5] and non_matches == [0, 2, 4]:
            return True
        return False
    
    def __str__(self):
        dt = datetime.utcfromtimestamp(self.start_time)
        return f"observation with id = {self.id} at utc = {dt} ({self.start_time})"

    def mjd(self):
        return Time(self.start_time, format="unix", scale="utc").mjd


class Connection(object):
    """
    Open a connection to bldw.
    """
    # We can cache this because it shouldn't change during a run
    cached_receivers = None

    def __init__(self):
        ini_path = os.path.join(DIR, "bldw.ini")
        lines = [line.strip() for line in open(ini_path)]
        config = dict(line.split("=") for line in lines if line)
        config["sslmode"] = "verify-ca"
        config["sslrootcert"] = os.path.join(DIR, "server-ca.pem")
        config["sslcert"] = os.path.join(DIR, "client-cert.pem")
        config["sslkey"] = os.path.join(DIR, "client-key.pem")
        self.conn = psycopg2.connect(**config)

    def print_schema(self, table_name):
        for row in self.fetchall("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = %s
        """, (table_name,)):
            print(row)

    def fetchone(self, command, args=()):
        cur = self.conn.cursor()
        cur.execute(command, args)
        result = cur.fetchone()
        cur.close()
        return result

    def fetchall(self, command, args=()):
        cur = self.conn.cursor()
        cur.execute(command, args)
        result = cur.fetchall()
        cur.close()
        return result

    def fetch_iter(self, command, args=()):
        cur = self.conn.cursor()
        cur.execute(command, args)
        for row in cur:
            yield row
        cur.close()

    def count_where(self, table, where, args=()):
        rows = self.fetchall(f"SELECT COUNT(*) from {table} WHERE {where}", args)
        assert len(rows) == 1
        return rows[0][0]

    def random_where(self, table, where, args=()):
        rows = self.fetchall(f"SELECT * from {table} WHERE {where} ORDER BY RANDOM() LIMIT 1", args)
        return rows[0]

    #### (meta)data ####
    def insert_meta(self, meta):
        assert meta.id is None
        cur = self.conn.cursor()
        # for key in dir(meta):
        #     print(f"type of meta.{key} is {type(getattr(meta, key))}")
        cur.execute("""INSERT into bl.data
        (observation_id, format, size, freq_low, freq_high, location, deleted, coarse_channels,
         fch1, foff, nbits, tstart, tsamp, nsamples, nchans, nifs)
        VALUES
        (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (meta.observation_id, meta.format, meta.size, meta.freq_low, meta.freq_high, meta.location,
              meta.deleted, meta.coarse_channels, meta.fch1, meta.foff, meta.nbits, meta.tstart, meta.tsamp,
              meta.nsamples, meta.nchans, meta.nifs))
        self.conn.commit()
        cur.close()

    def really_delete_meta(self, meta):
        """
        Delete meta from the database, not just marking it as deleted.
        """
        assert meta.id is not None
        cur = self.conn.cursor()
        cur.execute("DELETE from bl.data WHERE id = %s", (meta.id,))
        self.conn.commit()
        cur.close()
        
    def update_meta_observation_id(self, meta):
        assert meta.id is not None
        assert meta.observation_id is not None
        cur = self.conn.cursor()
        cur.execute("UPDATE bl.data SET observation_id = %s WHERE id = %s", (meta.observation_id, meta.id))
        self.conn.commit()
        cur.close()

    def update_meta_deleted(self, meta):
        assert meta.id is not None
        cur = self.conn.cursor()
        cur.execute("UPDATE bl.data SET deleted = %s WHERE id = %s", (meta.deleted, meta.id))
        self.conn.commit()
        cur.close()

    def random_metadata_where(self, where, args=()):
        return Metadata.from_row(self.random_where("bl.data", where, args=args))

    def fetch_metadata_where(self, where, args=()):
        rows = self.fetchall(f"SELECT * from bl.data WHERE {where}", args)
        return [Metadata.from_row(row) for row in rows]

    def iter_metadata_where(self, where, args=()):
        for row in self.fetch_iter(f"SELECT * from bl.data WHERE {where}", args):
            yield Metadata.from_row(row)

    def iter_random_metadata_where(self, where, args=()):
        """
        Order isn't random. Just starting point.
        """
        # First pick one random place to start
        start = self.random_metadata_where(self, where, args=args)
        # Then go in id order starting at start
        for row in self.fetch_iter(f"SELECT * from bl.data WHERE {where} AND id >= %s ORDER BY id", args + (start.id,)):
            yield Metadata.from_row(row)
        # Then do the ones we missed, from the beginning
        for row in self.fetch_iter(f"SELECT * from bl.data WHERE {where} AND id < %s ORDER BY id", args + (start.id,)):
            yield Metadata.from_row(row)

    def total_size_where(self, where, args=()):
        result = self.fetchone(f"SELECT SUM(size) from bl.data WHERE {where}", args)
        return result[0] or 0
            
    def fetch_metadata_by_location(self, location):
        """
        Raises a LookupError if there is no matching row.
        """
        rows = self.fetchall("SELECT * from bl.data WHERE location = %s", (location,))
        if not rows:
            raise LookupError(f"no row with location = {location}")
        if len(rows) > 1:
            raise RuntimeError(f"multiple rows with location = {location}")
        return Metadata.from_row(rows[0])

    def fetch_metadata_by_filename(self, filename):
        """
        Raises a LookupError if there is no matching row.
        """
        filename = os.path.normpath(filename)
        try:
            loc = machines.to_location(filename)
        except ValueError as e:
            raise LookupError(f"this file has an unsupported permanent location: {filename} ({e})")
        return self.fetch_metadata_by_location(loc)

    def fetch_recent_metadata(self, limit):
        """
        Returns the most recent Metadata objects.
        """
        rows = self.fetchall("SELECT * FROM bl.data ORDER BY tstart DESC LIMIT %s", (limit,))
        return [Metadata.from_row(row) for row in rows]

    def fetch_metadata_by_observation_id(self, obs_id):
        """
        Returns a list of Metadata that correspond to a particular observation id.
        """
        rows = self.fetchall("SELECT * from bl.data WHERE observation_id = %s", (obs_id,))
        return [Metadata.from_row(row) for row in rows]

    def fetch_metadata_by_size(self, size):
        return self.fetch_metadata_where("size = %s", (size,))
    
    def fetch_metadata_for_observation_ids(self, observation_ids):
        """
        Returns a list of Metadata that correspond to any of an iterable of observation ids.
        """
        rows = self.fetchall("SELECT * from bl.data WHERE observation_id IN %s", (tuple(observation_ids),))
        return [Metadata.from_row(row) for row in rows]

    def fetch_one_metadata_per_observation(self):
        """
        Returns a list of Metadata, one per observation, no particular metadata preferred.
        """
        rows = self.fetchall("SELECT DISTINCT ON (bl.data.observation_id) * from bl.data", ())
        return [Metadata.from_row(row) for row in rows]

    def fetch_iter_metadata(self, command, args=()):
        for row in self.fetch_iter("SELECT * from bl.data WHERE " + command, args=args):
            yield Metadata.from_row(row)
    
    def fetch_duplicate_metadata(self):
        """
        Iterates through a bunch of (green bank, berkeley) Metadata pairs that represent the same data
        and are both not deleted.
        """
        for big_row in self.fetch_iter("""
          SELECT * FROM bl.data t1, bl.data t2
            WHERE t1.size = t2.size
            AND t1.location LIKE %s
            AND t2.location LIKE %s
            AND t1.deleted = %s
            AND t2.deleted = %s
          """, ("file://gb%", "file://pd%", False, False)):
            mid = len(big_row) // 2
            left = big_row[:mid]
            right = big_row[mid:]
            gb_meta = Metadata.from_row(left)
            pd_meta = Metadata.from_row(right)
            if gb_meta.same_data(pd_meta):
                yield gb_meta, pd_meta
                
    #### observation ####
    def insert_observation(self, ob):
        cur = self.conn.cursor()
        cur.execute('INSERT into bl.observation VALUES (DEFAULT, %s, %s, %s, %s, %s, %s) returning *',
                    (ob.ra, ob.decl, ob.receiver_id, ob.start_time, ob.duration, ob.target_id))
        ob = cur.fetchone()
        self.conn.commit()
        cur.close()
        return Observation.from_row(ob)

    def update_observation_start_time(self, ob):
        assert ob.id is not None
        cur = self.conn.cursor()
        cur.execute("UPDATE bl.observation SET start_time = %s WHERE id = %s", (ob.start_time, ob.id))
        self.conn.commit()
        cur.close()

    def fetch_observations_where(self, where, args=()):
        rows = self.fetchall(f"SELECT * from bl.observation WHERE {where}", args)
        return [Observation.from_row(row) for row in rows]
                                 
    def fetch_observation(self, observation_id):
        observations = self.fetch_observations_where("id = %s", (observation_id,))
        if not observations:
            raise LookupError(f"no observation with id = {observation_id}")
        if len(observations) > 1:
            raise RuntimeError(f"multiple rows with observation id = {observation_id}")
        return observations[0]

    def fetch_observations(self, observation_ids):
        """
        Fetches observations matching any of the provided ids.
        """
        return self.fetch_observations_where("id IN %s", (tuple(observation_ids),))

    def fetch_all_observations(self):
        return [Observation.from_row(row) for row in self.fetchall("SELECT * from bl.observation")]

    def fetch_observations_by_tag_name(self, tag_name):
        return self.fetch_observations_where("""
          id in (select observation_id from bl.observation_tag where tag_id = (select id from bl.tag where name = %s))
        """, (tag_name,))

    def fetch_observations_by_target(self, target_id):
        return self.fetch_observations_where("target_id = %s", (target_id,))

    def fetch_observations_for_session(self, session):
        return self.fetch_observations_by_tag_name(session)

    def fetch_observation_after_timestamp(self, timestamp):
        observations = self.fetch_observations_where("start_time > %s ORDER BY start_time LIMIT 1", (timestamp,))
        return observations[0]

    def fetch_observation_before_timestamp(self, timestamp):
        observations = self.fetch_observations_where("start_time < %s ORDER BY -start_time LIMIT 1", (timestamp,))
        return observations[0]
    
    def guess_observation(self, h5file):
        """
        Guesses which observation corresponds to an h5 file.
        We heuristically check for an observation that starts at about the same time, and double-check that the information
        we find matches the filename.
        Raises a LookupError if our heuristics don't work.
        """
        filename = os.path.normpath(h5file.filename)
        timestamp = timestamp_from_h5(h5file)
        return self.guess_observation_by_timestamp(timestamp)
        
    def guess_observation_by_timestamp(self, timestamp):
        error_margin = 20 # seconds
        observations = self.fetch_observations_where("abs(start_time - %s) <= %s", (timestamp, error_margin))
        if len(observations) > 1:
            raise LookupError("multiple observations matched:\n" + "\n".join(map(str, observations)))
        if not observations:
            raise LookupError(f"no observation is close to file start time {timestamp}")
        return observations[0]

    def guess_session(self, h5file):        
        timestamp = timestamp_from_h5(h5file)
        try:
            obs = self.guess_observation_by_timestamp(timestamp)
            session = self.fetch_session_for_observation_id(obs.id)
            return session
        except LookupError:
            pass

        # If we don't have an exact observation, guess the closest one in time
        pre_obs = self.fetch_observation_before_timestamp(timestamp)
        post_obs = self.fetch_observation_after_timestamp(timestamp)
        assert pre_obs.start_time < timestamp
        assert timestamp < post_obs.start_time
        pre_distance = abs(pre_obs.start_time - timestamp)
        post_distance = abs(post_obs.start_time - timestamp)
        if pre_distance < post_distance:
            return self.fetch_session_for_observation_id(pre_obs.id)
        else:
            return self.fetch_session_for_observation_id(post_obs.id)
    
    #### target ####
    def insert_target(self, target):
        cur = self.conn.cursor()
        cur.execute('insert into bl.target VALUES (DEFAULT, %s, %s, %s, %s, %s, %s) returning *',
                    (target.name, target.ra, target.decl, target.pm_ra, target.pm_decl, target.epoch))
        target = cur.fetchone()
        self.conn.commit()
        cur.close()
        return Target.from_row(target)

    def fetch_targets_by_name(self, target_name):
        return self.fetch_targets_where('name = %s', (target_name,))
        
    def fetch_targets_where(self, where, args=()):
        rows = self.fetchall(f"SELECT * from bl.target WHERE {where}", args)
        return [Target.from_row(row) for row in rows]

    def fetch_target_dict(self, target_ids):
        """
        Returns a dictionary mapping target id to target.
        """
        answer = {}
        for target in self.fetch_targets_where("id IN %s", (tuple(target_ids),)):
            answer[target.id] = target
        return answer

    def fetch_target(self, target_id):
        targets = self.fetch_targets_where("id = %s", (target_id,))
        assert len(targets) == 1
        return targets[0]
    
    #### receiver ####
    def fetch_receivers(self):
        rows = self.fetchall("SELECT * from bl.receiver")
        return [Receiver.from_row(row) for row in rows]

    def fetch_receiver_by_name(self, name):
        if Connection.cached_receivers is None:
            Connection.cached_receivers = self.fetch_receivers()
        for receiver in Connection.cached_receivers:
            if receiver.name == name:
                return receiver
        raise LookupError(f"no receiver with name {name}")

    def fetch_receiver(self, receiver_id):
        if Connection.cached_receivers is None:
            Connection.cached_receivers = self.fetch_receivers()
        for receiver in Connection.cached_receivers:
            if receiver.id == receiver_id:
                return receiver
        raise LookupError(f"no receiver with id {receiver_id}")
    
    #### tag ####
    def fetch_tags_where(self, where, args=()):
        rows = self.fetchall(f"SELECT * from bl.tag WHERE {where}", args)
        return [Tag.from_row(row) for row in rows]

    def fetch_tags_for_observation_id(self, obs_id):
        return self.fetch_tags_where("""
          id in (select tag_id from bl.observation_tag where observation_id = %s)
        """, (obs_id,))

    def fetch_session_for_observation_id(self, obs_id):
        tags = self.fetch_tags_for_observation_id(obs_id)
        matching_tags = [tag for tag in tags if tag.type == "session"]
        if len(matching_tags) != 1:
            raise LookupError(f"unexpected tag list matching obs {obs_id} : {matching_tags}")
        return matching_tags[0].name
    
    def fetch_session_tag(self, session):
        try:
            return Tag.from_row(self.fetchone("select * from bl.tag where name = %s", (session,)))
        except TypeError:
            raise LookupError(f'No tag for {session}')

    def insert_session_tag(self, session):
        cur = self.conn.cursor()
        cur.execute('insert into bl.tag values (DEFAULT, %s, %s, %s) returning *', (session, None, 'session'))
        self.conn.commit()
        row = cur.fetchone()
        cur.close()
        return Tag.from_row(row)

    def create_or_fetch_session_tag(self, session):
        try:
            return self.fetch_session_tag(session)
        except LookupError:
            print("Creating new tag for " + session)
            return self.insert_session_tag(session)

    def insert_cadence_tag(self, cadence):
        """
        This returns the Tag because if you're creating one of these you're gonna use it to create more tags on other records.
        """
        cur = self.conn.cursor()
        cur.execute('insert into bl.tag values (DEFAULT, %s, %s, %s) returning *', (cadence, None, 'cadence'))
        self.conn.commit()
        row = cur.fetchone()
        cur.close()
        return Tag.from_row(row)

    #### target_tag
    def insert_target_tag(self, target_id, tag_id):
        cur = self.conn.cursor()
        cur.execute('insert into bl.target_tag values (DEFAULT, %s, %s)', (tag_id, target_id))
        self.conn.commit()
        cur.close()

    #### receiver_tag
    def insert_receiver_tag(self, receiver_id, tag_id):
        cur = self.conn.cursor()
        cur.execute('insert into bl.receiver_tag values (DEFAULT, %s, %s)', (tag_id, receiver_id))
        self.conn.commit()
        cur.close()

    #### observation_tag
    def insert_observation_tag(self, observation_id, tag_id):
        cur = self.conn.cursor()
        cur.execute('insert into bl.observation_tag values (DEFAULT, %s, %s)', (tag_id, observation_id))
        self.conn.commit()
        cur.close()

    def fetch_cadences_for_session(self, session):
        observations = self.fetch_observations_for_session(session)
        return Cadence.find_cadences(observations)

    #### priority
    def insert_priority(self, target_id, receiver_id, priority):
        cur = self.conn.cursor()
        cur.execute('insert into bl.priority values (DEFAULT, %s, %s, %s)', (target_id, receiver_id, priority))
        self.conn.commit()
        cur.close()

    #### other ####
    def fetch_cadence(self, cadence_id):
        # The cadence id is the id of the first observation in the cadence
        first_obs = self.fetch_observation(cadence_id)

        # The rest of the observations should be the next ones chronologically
        others = self.fetch_observations_where("start_time > %s ORDER BY start_time LIMIT 5", (first_obs.start_time,))

        observations = [first_obs] + others
        if not first_obs.is_cadence(observations):
            raise LookupError("the observations at id {cadence_id} do not form a cadence")
        return Cadence(observations)
    
    def all_sessions_with_files(self):
        return sorted(set(meta.session() for meta in self.fetch_one_metadata_per_observation()))

    def all_sessions(self):
        """
        Returns all sessions in sorted order.
        """
        def key(s):
            a, b, c = s.split("_")
            return (a, int(c))

        sessions_gen = (row[0] for row in self.fetchall("SELECT name FROM bl.tag WHERE type = %s", ("session",)))
        return sorted(sessions_gen, key=key)

    
def retry_connection():
    retries = 10
    for i in range(1, retries + 1):
        try:
            return Connection()
        except psycopg2.OperationalError as e:
            print(f"postgres connection failure {i}: {e}")
            if i == retries:
                raise
            time.sleep(10)
    raise RuntimeError("control should not reach here")
    
    
if __name__ == "__main__":
    conn = Connection()
    if sys.argv[1] == "listall":
        # List off all observations
        all_obs = conn.fetch_all_observations()
        print(f"bldw has {len(all_obs)} observations")
        for obs in all_obs:
            print(obs)
    elif sys.argv[1] == "distinct":
        metas = conn.fetch_one_metadata_per_observation()
        print(len(metas), "metas retrieved")
        for meta in metas:
            print(meta)
    elif sys.argv[1] == "sessions":
        for session in conn.all_sessions():
            print(session)
    elif len(sys.argv) > 1:
        # Fetch info for particular observations
        for arg in sys.argv[1:]:
            obs_id = int(arg)
            obs = conn.fetch_observation(obs_id)
            print(obs)
    else:
        print("some argument is required")
