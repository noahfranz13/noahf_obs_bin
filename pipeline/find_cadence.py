import sys, os
import bldw
import pandas as pd
import numpy as np
from cadence import good_cadences_for_session

def whichBand(cadence, tol=100):
    '''
    Return band of a given cadence
    '''

    meta = cadence.metas[0][0]
    print(meta)
    minf = meta.freq_low
    maxf = meta.freq_high

    L = [1100, 1900]
    S = [1800, 2800]
    C = [4000, 7800]
    X = [7800, 11200]

    if abs(minf-L[0]) < tol and abs(maxf-L[1]) < tol:
        return 'L'
    elif abs(minf-S[0]) < tol and abs(maxf-S[1]) < tol:
        return 'S'
    elif abs(minf-C[0]) < tol and abs(maxf-C[1]) < tol:
        return 'C'
    elif abs(minf-X[0]) < tol and abs(maxf-X[1]) < tol:
        return 'X'
    else:
        return 'NA'


def findCadences(targets, band='L'):

    c = bldw.Connection()

    targetObjs = [c.fetch_targets_by_name(tt)[0] for tt in targets]

    cadences = {}
    for tt in targetObjs:
        print()
        print("TARGET NAME: ", tt)
        print()
        observations = c.fetch_observations_by_target(tt.id)

        # get all the relevant session ids
        sessions = []
        for obs in observations:
            tags = c.fetch_tags_for_observation_id(obs.id)
            for tag in tags:
                if tag.name.startswith('AGBT'):
                    sessions.append(tag.name)

        # from a unique list of all of the sessions find the cadence and then filenames
        uqSessions = np.unique(np.array(sessions))
        cads = []
        for s in uqSessions:
            for cad in good_cadences_for_session(c, s):
                if len(cad.metas[0]) > 0 and band == whichBand(cad):
                    #print(cad)
                    cads.append(cad)


        for cad in cads:
            # TODO : Generalize for L, C, S, and X
            #metaList = cad.align_metas(1500) # for now select only L-band files
            #print(metaList)
            #if len(metaList) > 0:
                #cadences[tt.name] = [m.filename() for m in metaList[0]]
            print(cad.metas)
            cadences[tt.name] = [meta.filename() for meta in for metas in cad.metas]

    return cadences


def main():

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--targs', help='File with list of string target names to search for cadences for', default=None)
    args = parser.parse_args()

    targs = np.loadtxt(args.targs, dtype=str, delimiter='\n')

    cadences = findCadences(targs)
    print(cadences)
    #pd.DataFrame(cadences).to_csv(os.path.join(os.getcwd(), 'cadences.csv'))


if __name__ == '__main__':
    sys.exit(main())
