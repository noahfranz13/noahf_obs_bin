import sys, os
import bldw
import pandas as pd
import numpy as np
from cadence import good_cadences_for_session

def findCadences(targets, band='L'):

    c = bldw.Connection()

    targetObjs = [c.fetch_targets_by_name(tt)[0] for tt in targets]

    rcvr = c.fetch_receiver_by_name('Rcvr1_2') # change so that the receiver changes depending on the requested band
    print()
    print('Searching for files observed with: ', rcvr.name)

    cadences = {}
    for tt in targetObjs:
        print()
        print("CADENCE FOR : ", tt)
        print()

        observations = c.fetch_observations_by_target(tt.id)

        # get all the relevant session ids
        sessions = []
        for obs in observations:
            if c.fetch_receiver(obs.receiver_id).name == rcvr.name:
                tags = c.fetch_tags_for_observation_id(obs.id)
                for tag in tags:
                    if tag.name.startswith('AGBT'):
                        sessions.append(tag.name)

        # from a unique list of all of the sessions find the cadence and then filenames
        uqSessions = np.unique(np.array(sessions))
        cads = []
        for s in uqSessions:
            for cad in good_cadences_for_session(c, s):
                cads.append(cad)

        for cad in cads:
            for metas in cad.metas:
                for meta in metas:
                    print("Found: ", meta.filename())
                    if tt.name in cadences.keys():
                        cadences[tt.name].append(meta.filename())
                    else:
                        cadences[tt.name] = [meta.filename()]

    return cadences


def main():

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--targName', help='Name of single target you want to find a cadence for', default=None)
    parser.add_argument('--targs', help='File with list of string target names to search for cadences for', default=None)
    args = parser.parse_args()

    if args.targName:
        targs = [args.targName]
    elif args.targs:
        targs = np.loadtxt(args.targs, dtype=str, delimiter='\n')
    else:
        raise ValueError("Please either provide a singular target name or file with list of targets")

    cadences = findCadences(targs)
    print(cadences)
    #pd.DataFrame(cadences).to_csv(os.path.join(os.getcwd(), 'cadences.csv'))


if __name__ == '__main__':
    sys.exit(main())
