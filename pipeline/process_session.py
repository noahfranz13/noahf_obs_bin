#!/usr/bin/env python
"""
idempotent
for each session (in bls0:/datax/gbtdata/<semester>/):
    create session tag
    for each fits file in session (.../<session>/GO/):
        create target (if necessary)
        create observation record
            tag as part of session
    for each set of six consecutive observations:
        if cadence:
            create cadence tag
            tag all six observations as part of this cadence
"""
import argparse
import datetime
import os
import numpy
import pandas

from astropy.io import fits

import bldw
import simbad

DIR_PREFIX = '/datax/gbtdata/'
GO_DIR = '/GO/'
ANTENNA_DIR = '/Antenna/'

TARGET_CADENCE_OBSERVATION_TUPLES_QUERY = """
select target_id, bl.tag.id, observation_id
from bl.tag join bl.observation_tag on bl.tag.id = bl.observation_tag.tag_id join bl.target_tag on bl.tag.id = bl.target_tag.tag_id
where type = %s and observation_id in (select observation_id from bl.observation_tag where tag_id = %s)
"""

conn = bldw.Connection()

#### helper functions ####

def cadence_name(primary_target_name, observations):
    last_observation_timestamp = datetime.datetime.fromtimestamp(observations[5].start_time).strftime("%Y-%m-%dT%H:%M:%SZ")
    first_observation_id = observations[0].id
    return f'{primary_target_name}@{last_observation_timestamp}_{first_observation_id}'

def primary_targets(cadence):
    target_ids = [o.target_id for o in cadence]
    first = target_ids[0]
    second = target_ids[1]
    first_count = target_ids.count(first)
    second_count = target_ids.count(second)
    if first_count == 3 and second_count != 3:
        return [first]
    if second_count == 3 and first_count != 3:
        return [second]
    if first_count == 3 and second_count == 3:
        return [first, second]
    raise Exception(f'no targets with three scans for cadence starting {cadence[0].id}')

def get_ant_coords(ant):
    df = pandas.DataFrame(ant[2].data)
    ra = df['RAJ2000'].median() / 15.0
    decl = df['DECJ2000'].median()
    return ra, decl

def get_go_coords(go):
    ra, decl = None, None
    try:
        ra = go[0].header['RA'] / 15.0
        decl = go[0].header['DEC']
    except:
        pass
    return ra, decl

def get_target_coords(target):
    return target.ra, target.decl

def get_receiver(go):
    return conn.fetch_receiver_by_name(go[0].header['RECEIVER'])

def create_target(target_name, go, ant):
    ra, decl, pm_ra, pm_decl, epoch = None, None, None, None, None
    simbad_results = simbad.query_object(target_name)
    simbad_target = None
    if simbad_results:
        for i, r in enumerate(simbad_results):
            print(i)
            print(r)
        results_choice = input(f'Enter the index of the best candidate for {target_name} or anything else to discard and create target from fits data: ')
        try:
            index = int(results_choice)
            simbad_target = simbad_results[index]
        except ValueError:
            pass

    if simbad_target:
        ra_degs = simbad_target[simbad.RA_KEY]
        sig_figs = len(str(ra_degs))
        ra_hrs = ra_degs / 15.0
        ra = float(numpy.format_float_positional(ra_hrs, precision=sig_figs))
        decl = float(simbad_target[simbad.DECL_KEY])
        pm_ra_col = simbad_target[simbad.PM_RA_KEY]
        pm_ra = float(pm_ra_col) if isinstance(pm_ra_col, numpy.float64) else None
        pm_decl_col = simbad_target[simbad.PM_DECL_KEY]
        pm_decl = float(pm_decl_col) if isinstance(pm_decl_col, numpy.float64) else None
        epoch = 'J2000'
    else:
        if simbad_results:
            print(f'Simbad candidate(s) for {target_name} discarded.')
        else:
            print(f'No simbad entry for {target_name}')
        print('Creating target from fits file data.')

    if not ra:
        ra, decl = get_go_coords(go)
    if not ra:
        ra, decl = get_ant_coords(ant)
    if not ra:
        raise Exception(f'Failed to create target for {target_name} after trying simbad, GO, and Antenna')

    target = bldw.Target.from_vals(None, target_name, ra, decl, pm_ra, pm_decl, epoch)
    print(f'Creating target for {target_name}')
    return conn.insert_target(target)

def get_target(go, ant):
    target_name = go[0].header['OBJECT'].upper()
    if target_name.startswith('DIAG_'):
        target_name = target_name[5:]
    targets = conn.fetch_targets_by_name(target_name)
    if len(targets) == 1:
        return targets[0]
    targets = conn.fetch_targets_where('name like %s', (f'%{target_name}%',))
    if len(targets) == 0:
        return create_target(target_name, go, ant)
    else:
        for i, t in enumerate(targets):
            print(i)
            print(t)
        choice = input(f"Enter the index of the best candidate for {target_name} or anything else to create a new one: ")
        try:
            index = int(choice)
            return targets[index]
        except ValueError:
            return create_target(target_name, go, ant)

#### end helper functions

assert __name__ == '__main__'

parser = argparse.ArgumentParser()
parser.add_argument('semester')
parser.add_argument('--session')

args = parser.parse_args()
path = DIR_PREFIX + args.semester + '/'
sessions = []
if args.session:
    sessions.append(args.session)
else:
    sessions = os.listdir(path)

#### iterate through each fits file in the session(s) and create an observation
#### record if one does not already exist
#### then, create cadence tags if not present
for sesh in sessions:
    session_tag = conn.create_or_fetch_session_tag(sesh)
    observations = conn.fetch_observations_for_session(sesh)
    timestamp_map = {}
    for o in observations:
        timestamp_map[o.start_time] = o
    go_path = path + sesh + GO_DIR
    ant_path = path + sesh + ANTENNA_DIR
    try:
        os.listdir(go_path)
    except:
        print('No GO dir for ' + sesh)
        continue
    for obs in os.listdir(go_path):
        if not obs.endswith('.fits'):
            print('Skipping non-fits file: ' + go_path + obs)
            continue
        go = None
        try:
            go = fits.open(go_path + obs)
        except OSError as err:
            print(go_path + obs + ' ' + str(err.strerror))
            continue
        ant = None
        try:
            ant = fits.open(ant_path + obs)
        except:
            pass
        timestamp = int(datetime.datetime.fromisoformat(go[0].header['DATE-OBS'] + '+00:00').timestamp())
        if timestamp < 0:
            print(f'{go_path}{obs} has negative timestamp: {timestamp}')
            continue
        if not timestamp_map.get(timestamp):
            receiver = get_receiver(go)
            target = get_target(go, ant)
            ra, decl = None, None
            if ant:
                ra, decl = get_ant_coords(ant)
            if not ra or numpy.isnan(ra):
                ra, decl = get_go_coords(go)
            if not ra or numpy.isnan(ra):
                ra, decl = get_target_coords(target)
            obs = bldw.Observation.from_vals(None, ra, decl, receiver.id, timestamp, None, target.id)
            obs = conn.insert_observation(obs)
            conn.insert_observation_tag(obs.id, session_tag.id)

    #### Record cadences
    observations = sorted(conn.fetch_observations_for_session(sesh), key=lambda x: x.start_time)
    target_cadence_observation_tuples = conn.fetchall(TARGET_CADENCE_OBSERVATION_TUPLES_QUERY, ('cadence', session_tag.id))
    target_cadence_map = {}
    for t in target_cadence_observation_tuples:
        target_id, cadence_id, observation_id = t
        if target_id not in target_cadence_map:
            target_cadence_map[target_id] = {}
        if cadence_id not in target_cadence_map[target_id]:
            target_cadence_map[target_id][cadence_id] = set()
        target_cadence_map[target_id][cadence_id].add(observation_id)
    for i in range(len(observations) - 6):
        candidate = observations[i:i+6]
        if bldw.Observation.is_cadence(candidate):
            primary_target_ids = primary_targets(candidate)
            observation_id_set = set(o.id for o in candidate)
            for pid in primary_target_ids:
                already_exists = False
                if pid in target_cadence_map:
                    for _, cadence_observation_id_set in target_cadence_map[pid].items():
                        if observation_id_set == cadence_observation_id_set:
                            already_exists = True
                            break
                if already_exists:
                    continue
                cadence_tag = conn.insert_cadence_tag(cadence_name(conn.fetch_target(pid).name, candidate))
                for o in candidate:
                    conn.insert_observation_tag(o.id, cadence_tag.id)
                conn.insert_target_tag(pid, cadence_tag.id)
                conn.insert_receiver_tag(candidate[0].receiver_id, cadence_tag.id)
