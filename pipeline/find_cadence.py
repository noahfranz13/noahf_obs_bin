import sys, os
import bldw
import pandas as pd
import numpy as np
from cadence import good_cadences_for_session


def findCadences(targets):

    c = bldw.Connection()

    targetObjs = [c.fetch_targets_by_name(tt)[0] for tt in targets]

    cadences = {}
    for tt in targetObjs:

        observations = c.fetch_observations_by_target(tt.id)
        sessions = []
        for obs in observations:

            tags = c.fetch_tags_for_observation_id(obs.id)
            for tag in tags:
                if tag.name.startswith('AGBT'):
                    sessions.append(tag.name)
        print(sessions)
        for s in sessions:
            for cad in good_cadences_for_session(c, s):
                metaList = cad.align_metas(1500)
                if len(metaList) > 0:
                    cadences[tt.name] = [m.filename() for m in metaList[0]]

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
