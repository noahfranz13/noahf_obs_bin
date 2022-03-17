import sys, os
import bldw
import pandas as pd
import numpy as np
from cadence import good_cadences_for_session

def findCadences(targets, band):

    c = bldw.Connection()

    targetObjs = [c.fetch_targets_by_name(tt)[0] for tt in targets]

    # get receiver based on input band
    if band == 'L':
        rcvr = c.fetch_receiver_by_name('Rcvr1_2')
    elif band == 'S':
        rcvr = c.fetch_receiver_by_name('Rcvr2_3')
    elif band == 'C':
        rcvr = c.fetch_receiver_by_name('Rcvr1_2') # FIX THIS
    elif band == 'X':
        rcvr = c.fetch_receiver_by_name('Rcvr1_2') # FIX THIS
    else:
        raise ValueError("Provide valid band")

    print()
    print('Searching for files observed with: ', rcvr.name)

    for tt in targetObjs:
        print()
        print("CADENCE FOR : ", tt.name)

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

        # get correct cadence
        goodCad = None
        for cad in cads:
            for metas in cad.metas:
                if len(metas) > 0:
                    meta = metas[0] # get filename of first observation in the cadence
                    targetname = meta.filename().split('/')[-1].split('_')[-2]
                    if targetname == tt.name:
                        print(targetname, tt.name)
                        goodCad = cad
                        break

        # create dictionary of cadences based on the observations
        cadenceList = []
        if not goodCad:
            print("Can not find information on this target...")
            print("You will need to find session ", uqSessions, " on your own, sorry")
        else:
            for metas in goodCad.metas:
                for meta in metas:
                    file = meta.filename()
                    print("Found: ", file)
                    cadenceList.append(file)

        # check the file paths in the cadence dictionary so that each cadence only has 6 files
        if len(cadenceList) > 6:
            betterCadenceList = []
            for path in cadenceList:
                if path[0:6] == '/datag' and path[-7:-3] == '0000':
                    betterCadenceList.append(path)

            cadenceList = betterCadenceList

        if len(cadenceList) > 0:
            outfile = os.path.join(os.getcwd(), f'{tt.name}-cadence.txt')
            np.savetxt(outfile, np.array(cadenceList), fmt='%s', delimiter=',',)

    return cadences


def main():

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--targName', help='Name of single target you want to find a cadence for', default=None)
    parser.add_argument('--targs', help='File with list of string target names to search for cadences for', default=None)
    parser.add_argument('--band', help='frequency band to find cadence at, must be L, C, S, or X', default=None)
    args = parser.parse_args()

    if args.targName:
        targs = [args.targName]
    elif args.targs:
        targs = np.loadtxt(args.targs, dtype=str, delimiter='\n')
    else:
        raise ValueError("Please either provide a singular target name or file with list of targets")

    if not args.band or (args.band not in ('L', 'C', 'S', 'X')):
        raise ValueError("Please provide valid band, L, S, C, or X")

    findCadences(targs, band=args.band)
    #print(cadences)
    # pd.DataFrame(cadences).to_csv(os.path.join(os.getcwd(), 'cadences.csv'))

if __name__ == '__main__':
    sys.exit(main())
